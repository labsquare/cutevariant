from cutevariant.core import sql
import sqlite3
import re

def filters_to_flat(filters: dict):
    """Recursive function to convert the filter hierarchical dictionnary into a list of fields

    Args:
        filter (dict): a nested tree of condition. @See example

    Returns:
        Return (list): all field are now inside a a list 

    Todo:
        Move to vql ? 

    Examples:
        filters = {'AND': 
        [{'field': 'ref', 'operator': '=', 'value': "A"},
        {'field': 'alt', 'operator': '=', 'value': "C"}]
        }
        
        filters = _flatten_filter(filters)

        # filters is now [{'field': 'ref', 'operator': '=', 'value': "A"},{'field': 'alt', 'operator': '=', 'value': "C"}]] 
    """
    def recursive_generator(filters):
        if isinstance(filters, dict) and len(filters) == 3:
            yield filters

        if isinstance(filters, dict):
            for i in filters:
                yield from recursive_generator(filters[i])

        if isinstance(filters, list):
            for i in filters:
                yield from recursive_generator(i)

    return list(recursive_generator(filters))


def field_function_to_sql(field_function: tuple):
    ''' Convert genotype(boby).GT to `genotype_boby`.GT ''' 
    func_name, arg_name, field_name = field_function 
    if field_name:
        return f"`{func_name}_{arg_name}`.`{field_name}`"
    else:
        return f"`{func_name}_{arg_name}`"


def fields_to_sql(field, default_tables = {}):
    """
    Return field as sql syntax . 
    
    Args:
        field (str or tuple): Column name from a table 
        default_tables (dict, optional): association between field name and table origin 
    
    Returns:
        str: Sql field 

    Examples: 
        fields_to_sql("chr", {"chr":variants})  => `variants`.`chr` 
    """

    if isinstance(field, tuple):
        return field_function_to_sql(field)

    # extract variants.chr  ==> (variant, chr)
    match = re.match(r"^(\w+)\.(\w+)", field)

    if match: 
        table = match[1]
        field = match[2]
    else:
        if field in default_tables.keys():
            table = default_tables[field]
        else:
            return f"`{field}`"

    return f"`{table}`.`{field}`"


def filters_to_sql(filters, default_tables = {}):


    def is_field(node):
        return True if len(node) == 3 else False

    def recursive(node):
        if not node:
            return ""

        if is_field(node):
            field = node["field"]
            value = node["value"]
            operator = node["operator"]

            # quote string 
            if isinstance(field, str):
                value = f"'{value}'"

            if operator == "~":
                operator="REGEXP"

            if operator == "has":
                operator = "LIKE"
                # replace  "'test' " =>  "'%test%' "
                value = "'" + value.translate(str.maketrans("'\"","%%"))  + "'"

                

            field = fields_to_sql(field, default_tables)
        
            # TODO ... c'est degeulasse ....
            if operator in ("IN", "NOT IN"):
                # DO NOT enclose value in quotes
                # node: {'field': 'ref', 'operator': 'IN', 'value': "('A', 'T', 'G', 'C')"}
                # wanted: ref IN ('A', 'T', 'G', 'C')
                pass

            elif isinstance(value, list):
                value = "(" + ",".join(value) + ")"
            else:
                value = str(value)

            # There must be spaces between these strings because of strings operators (IN, etc.)
            return "%s %s %s" % (field, operator, value)
        else:
            # Not a field: 1 key only: the logical operator
            logic_op = list(node.keys())[0]
            # Recursive call for each field in the list associated to the
            # logical operator.
            # node:
            # {'AND': [
            #   {'field': 'ref', 'operator': 'IN', 'value': "('A', 'T', 'G', 'C')"},
            #   {'field': 'alt', 'operator': 'IN', 'value': "('A', 'T', 'G', 'C')"}
            # ]}
            # Wanted: ref IN ('A', 'T', 'G', 'C') AND alt IN ('A', 'T', 'G', 'C')
            out = [recursive(child) for child in node[logic_op]]
            # print("OUT", out, "LOGIC", logic_op)
            # OUT ["refIN'('A', 'T', 'G', 'C')'", "altIN'('A', 'T', 'G', 'C')'"]
            if len(out) == 1:
                return f" {logic_op} ".join(out)
            else:
                return "(" + f" {logic_op} ".join(out) + ")"

    return recursive(filters)



def build_query(columns, 
    source = "variants", 
    filters = {}, 
    order_by = None, 
    order_desc = True,
    grouped = False,
    limit = 50,
    offset = 0,
    default_tables = {}):

    sql_query = ""
    # Create columns 
    sql_columns = ["`variants`.`id`"] + [fields_to_sql(col, default_tables) for col in columns if "id" not in col]
    sql_query = f"SELECT {','.join(sql_columns)} "

    # Add child count if grouped 
    if grouped:
        sql_query += ", COUNT(*) as `children`"

    #  Add source table
    sql_query += f"FROM variants"

    # Extract columns from filters 
    columns_in_filters = [i["field"] for i in filters_to_flat(filters)]
    
    # Loop over columns and check is annotations is required 
    need_join_annotations = False
    for col in sql_columns + columns_in_filters:
        print(col)
        if "annotations" in col:
            need_join_annotations = True
            break

    if need_join_annotations:
        sql_query += (
            " LEFT JOIN annotations ON annotations.variant_id = variants.id"
        )

    #  Add Join Selection
    # TODO: set variants as global variables
    if source != "variants":
        sql_query += (
            " INNER JOIN selection_has_variant sv ON sv.variant_id = variants.id "
            f"INNER JOIN selections s ON s.id = sv.selection_id AND s.name = '{source}'"
        )

    #  Add Join Samples
    ## detect if columns contains function like (genotype,boby,gt) and save boby
    all_columns = columns_in_filters + columns
    samples = []
    for col in all_columns:
        if isinstance(col, tuple):
            if col[0] == "genotype":
                samples.append(col[1])

    ## Create Sample Join
    for sample_name in samples:
        # Optimisation ? 
        #sample_id = self.cache_samples_ids[sample_name]
        sql_query += (
            f" INNER JOIN sample_has_variant `genotype_{sample_name}` ON `genotype_{sample_name}`.variant_id = variants.id"
            f" INNER JOIN samples ON samples.name = '{sample_name}' AND `genotype_{sample_name}`.sample_id = samples.id"
        )

    #  Add Where Clause
    if filters:
        where_clause = filters_to_sql(filters, default_tables)
        # TODO : filter_to_sql should returns empty instead of ()
        if where_clause and where_clause != "()":
            sql_query += " WHERE " + where_clause

    #  Add Group By
    if grouped:
        sql_query += " GROUP BY " + ",".join(["chr","pos","ref","alt"])

    #  Add Order By
    if order_by:
        # TODO : sqlite escape field with quote
        orientation = "DESC" if order_desc else "ASC"
        order_by = fields_to_sql(order_by, default_tables)
        sql_query += f" ORDER BY {order_by} {orientation}"

    if limit:
        sql_query += f" LIMIT {limit} OFFSET {offset}"

    return sql_query


