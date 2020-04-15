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