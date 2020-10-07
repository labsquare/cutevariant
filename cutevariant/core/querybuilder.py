"""Functions to build a complex SQL Select statement to query variant.

In the most of cases, you will only use build_query function.

Examples:

    conn = sqlite3.Connection("::memory::")
    query = build_query(["chr","pos"])
    conn.execute(query)

"""
# Standard imports
import sqlite3
import re

# Custom imports
from cutevariant.core import sql

# Function name used from VQL
# sample("boby").gt
# TODO : can be move somewhere else . In common ?
GENOTYPE_FUNC_NAME = "sample"

# set("truc")
SET_FUNC_NAME = "SET"


def filters_to_flat(filters: dict):
    """Recursive function to convert the filter hierarchical dictionnary into a list of fields

    Args:
        filter (dict): a nested tree of condition. @See example

    Returns:
        Return (list): all field are now inside a a list

    Todo:
        Move to vql ?

    Examples:
        filters = {
            'AND': [
                {'field': 'ref', 'operator': '=', 'value': "A"},
                {'field': 'alt', 'operator': '=', 'value': "C"}
            ]
        }

        filters = _flatten_filter(filters)

        filters is now:
        [
            {'field': 'ref', 'operator': '=', 'value': "A"},
            {'field': 'alt', 'operator': '=', 'value': "C"}
        ]
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


def field_function_to_sql(field_function: tuple, use_as=False):
    """Convert VQL function to a a jointure field name

    Examples:

        # which correspond to genotype(boby).GT in VQL
        field = ("genotype", "boby","gt")
        field_function_to_sql(field) == `genotype_boby`.GT

    """
    func_name, arg_name, field_name = field_function

    if use_as:
        suffix = f" AS '{func_name}.{arg_name}.{field_name}'"
    else:
        suffix = ""

    if field_name:
        return f"`{func_name}_{arg_name}`.`{field_name}`" + suffix
    return f"`{func_name}_{arg_name}`" + suffix


def set_function_to_sql(field_function: tuple):
    """Replace a set_function by a select statement

    Set_functions is used from VQL to filter annotation within a set of word.
    For instance : " SELECT ... WHERE gene IN SET("boby") "
    will be replaced by "SELECT ... WHERE gene IN ( SELECT value FROM sets WHERE name = 'boby')

    Returns:
        (str): Query statement
    """
    func_name, arg_name = field_function
    return f"(SELECT value FROM sets WHERE name = '{arg_name}')"


def fields_to_vql(field):

    if isinstance(field, str):
        return field

    if isinstance(field, tuple):
        if field[0] == GENOTYPE_FUNC_NAME and len(field) == 3:
            return f"{field[0]}['{field[1]}'].{field[2]}"


def fields_to_sql(field, default_tables={}, use_as=False):
    """Return field as sql syntax

    Args:
        field (str or tuple): Column name from a table
        default_tables (dict, optional): association between field name and table origin

    Returns:
        str: Sql field

    Examples:
        fields_to_sql("chr", {"chr":variants})  => `variants`.`chr`
    """
    if isinstance(field, tuple):

        # If it is "genotype.name.truc then it is is field function"
        return field_function_to_sql(field, use_as)

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


def filters_to_sql(filters, default_tables={}):
    """Return filters as sql syntax

    Args:
        filters (dict): Nested tree of condition
        default_tables (dict, optional): association between field name and table origin

    Returns:
        str: SQL WHERE expression

    Examples:
        filters_to_sql({"AND": [("pos",">",34), ("af", "==", 10]}) == 'pos > 34 AND af = 10

    Note:
        There is a recursive function inside to parse the nested tree of conditions
    """

    def is_field(node):
        return len(node) == 3

    def recursive(node):
        if not node:
            return ""

        if is_field(node):
            field = node["field"]
            value = node["value"]
            operator = node["operator"].upper()

            # quote string
            if isinstance(value, str):
                value = f"'{value}'"

            if isinstance(value, tuple):
                if value[0] == SET_FUNC_NAME:
                    value = set_function_to_sql(value)

            if operator == "~":
                operator = "REGEXP"

            if operator == "HAS":
                operator = "LIKE"
                # replace  "'test' " =>  "'%test%' "
                value = "'" + value.translate(str.maketrans("'\"", "%%")) + "'"

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
        return "(" + f" {logic_op} ".join(out) + ")"

    return recursive(filters)


def filters_to_vql(filters):
    """Same than filters_to_sql but generates a VQL expression

    It means no SQL transformations are made
    """

    def is_field(node):
        return len(node) == 3

    def recursive(node):
        if not node:
            return ""

        if is_field(node):
            field = fields_to_vql(node["field"])
            value = node["value"]
            operator = node["operator"]

            if isinstance(value, str):
                value = f"'{value}'"

            if isinstance(value, tuple):
                # if set   ["set", "name"]
                if len(value) == 2 and value[0] == SET_FUNC_NAME:
                    value = "{}['{}']".format(SET_FUNC_NAME, value[1])

            return "%s %s %s" % (field, operator, value)

        # Not a field: 1 key only: the logical operator
        logic_op = list(node.keys())[0]

        out = [recursive(child) for child in node[logic_op]]
        # print("OUT", out, "LOGIC", logic_op)
        # OUT ["refIN'('A', 'T', 'G', 'C')'", "altIN'('A', 'T', 'G', 'C')'"]
        # if len(out) == 1:
        #     return f" {logic_op} ".join(out)
        # else:
        return "(" + f" {logic_op} ".join(out) + ")"

    query = recursive(filters)[1:-1]

    return query


def build_vql_query(fields, source="variants", filters={}, group_by=[], having={}):
    """Build VQL query

    TODO : harmonize name with build_query => build_sql

    Args:
        fields (TYPE): Description
        source (str, optional): Description
        filters (dict, optional): Description
    """
    query = "SELECT " + ",".join([fields_to_vql(i) for i in fields]) + " FROM " + source
    if filters:
        query += " WHERE " + filters_to_vql(filters)

    if group_by:
        query += " GROUP BY " + ",".join(group_by)

        if having:
            operator = having["op"]
            value = having["value"]
            query += f" HAVING count {operator} {value}"

    return query


def build_query(
    fields,
    source="variants",
    filters={},
    order_by=None,
    order_desc=True,
    limit=50,
    offset=0,
    group_by=[],
    having={},  # {"op":">", "value": 3  }
    default_tables={},
    samples_ids={},
):
    """Build SQL SELECT query on variants tables

    Args:
        fields (list): List of fields
        source (str): source of the virtual table ( see: selection )
        filters (dict): nested condition tree
        order_by (str/None): Order by field;
        If None, order_desc is not required.
        order_desc (bool): Descending or Ascending order
        limit (int/None): limit record count;
        If None, offset is not required.
        offset (int): record count per page
        group_by (list/None): list of field you want to group
        default_tables (dict): association map between fields and sql table origin
        samples_ids (dict): association map between samples name and id
    """
    # Create fields
    sql_fields = ["`variants`.`id`"] + [
        fields_to_sql(col, default_tables, use_as=True) for col in fields if col != "id"
    ]

    # if group_by:
    #     sql_fields.insert(1, "COUNT() as 'count'")

    sql_query = f"SELECT DISTINCT {','.join(sql_fields)} "

    # #Add child count if grouped
    # if grouped:
    #     sql_query += ", COUNT(*) as `children`"

    # Add source table
    sql_query += "FROM variants"

    # Extract fields from filters
    fields_in_filters = [i["field"] for i in filters_to_flat(filters)]

    # Loop over fields and check is annotations is required

    annotation_fields = [i for i, v in default_tables.items() if v == "annotations"]

    need_join_annotations = False
    for col in sql_fields + fields_in_filters:
        if "annotations" in col or col in annotation_fields:
            need_join_annotations = True
            break

    if need_join_annotations:
        sql_query += " LEFT JOIN annotations ON annotations.variant_id = variants.id"

    # Add Join Selection
    # TODO: set variants as global variables
    if source != "variants":
        sql_query += (
            " INNER JOIN selection_has_variant sv ON sv.variant_id = variants.id "
            f"INNER JOIN selections s ON s.id = sv.selection_id AND s.name = '{source}'"
        )

    # Add Join Samples
    ##detect if fields contains function like (genotype,boby,gt) and save boby

    all_fields = set(fields_in_filters + fields)

    samples = []
    for col in all_fields:
        # if column looks like  "genotype.tumor.gt"
        if isinstance(col, tuple):
            if col[0] == GENOTYPE_FUNC_NAME:
                sample_name = col[1]
                samples.append(sample_name)

    # make samples uniques
    samples = set(samples)

    ## Create Sample Join

    for sample_name in samples:
        # Optimisation ?
        # sample_id = self.cache_samples_ids[sample_name]
        if sample_name in samples_ids:
            sample_id = samples_ids[sample_name]
            sql_query += f""" INNER JOIN sample_has_variant `{GENOTYPE_FUNC_NAME}_{sample_name}` ON `{GENOTYPE_FUNC_NAME}_{sample_name}`.variant_id = variants.id AND `{GENOTYPE_FUNC_NAME}_{sample_name}`.sample_id = {sample_id}"""

    # Add Where Clause
    if filters:
        where_clause = filters_to_sql(filters, default_tables)
        # TODO : filter_to_sql should returns empty instead of ()
        if where_clause and where_clause != "()":
            sql_query += " WHERE " + where_clause

    # Add Group By
    if group_by:
        sql_query += " GROUP BY " + ",".join(
            [fields_to_sql(g, default_tables, use_as=False) for g in group_by]
        )
        if having:
            operator = having["op"]
            val = having["value"]
            sql_query += f" HAVING count {operator} {val}"

    # Add Order By
    if order_by:
        # TODO : sqlite escape field with quote
        orientation = "DESC" if order_desc else "ASC"
        order_by = fields_to_sql(order_by, default_tables)
        sql_query += f" ORDER BY {order_by} {orientation}"

    if limit:
        sql_query += f" LIMIT {limit} OFFSET {offset}"

    return sql_query


def build_complete_query(
    conn: sqlite3.Connection,
    fields=["chr", "pos", "ref", "alt"],
    source="variants",
    filters=dict(),
    order_by=None,
    order_desc=True,
    group_by=[],
    having={},  # {"op":">", "value": 3  }
    limit=50,
    offset=0,
    **kwargs,
):
    """Build a complete select statements according data loaded from conn"""
    default_tables = {i["name"]: i["category"] for i in sql.get_fields(conn)}
    samples_ids = {i["name"]: i["id"] for i in sql.get_samples(conn)}
    query = build_query(
        fields=fields,
        source=source,
        filters=filters,
        order_by=order_by,
        order_desc=order_desc,
        limit=limit,
        offset=offset,
        group_by=group_by,
        having=having,
        default_tables=default_tables,
        samples_ids=samples_ids,
    )
    return query
