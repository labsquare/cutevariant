"""Functions to build a complex SQL Select statement to query variant.

In the most of cases, you will only use build_sql_query function.

Examples

    conn = sqlite3.Connection("::memory::")
    query = build_sql_query(fields, source, filters)
    conn.execute(query)

Fields contains columns to select according sql table that they belong to.

    {
    "variants": ["chr","pos","ref"]
    "annotations": ["gene","impact"],
    "samples": [
        {"name":"boby", "fields":["gt","dp"]},
        {"name":"boby", "fields":["gt","dp"]}
    ]
    }

"""
# Standard imports
import sqlite3
import re
from functools import lru_cache
from ast import literal_eval

# Custom imports
from cutevariant.core import sql


from cutevariant import LOGGER

# TODO : can be move somewhere else ? In common ?
# Function names used in VQL
# sample["boby"].gt
# WORDSET["truc"]
WORDSET_FUNC_NAME = "WORDSET"

OPERATORS = {
    "$eq": "=",
    "$gt": ">",
    "$gte": ">=",
    "$lt": "<",
    "$lte": "<=",
    "$in": "IN",
    "$ne": "!=",
    "$nin": "NOT IN",
    "$regex": "REGEXP",
    "$and": "AND",
    "$or": "OR",
    "$has": "HAS",
}


def filters_to_flat(filters: dict):
    """Recursive function to convert the filter hierarchical dictionnary into a list of fields

    Examples::

        filters = {
            '$and': [
                {"ref":"A"},
                {"alt","C"}
            ]
        }

        filters = _flatten_filter(filters)

        filters is now:
        [
            {"ref":"A", "alt":"C"}
        ]
    """

    flatten = []
    for k, v in filters.items():
        if isinstance(v, list):
            for i in v:
                flatten += filters_to_flat(i)

        else:
            if filters not in flatten:
                flatten.append(filters)

    return flatten


def is_annotation_join_required(fields, filters) -> bool:
    """Return True if SQL join annotation is required

    Args:
        fields (TYPE): Description
        filters (TYPE): Description

    Returns:
        bool: Description
    """

    for field in fields:
        if field.startswith("ann."):
            return True

    for condition in filters_to_flat(filters):

        condition = list(condition.keys())[0]
        if condition.startswith("ann."):
            return True

    return False


def samples_join_required(fields, filters) -> list:
    """Return sample list of sql join is required

    Args:
        field (TYPE): Description
        filters (TYPE): Description

    Returns:
        list: Description
    """
    samples = set()

    for field in fields:
        if field.startswith("samples"):
            _, *sample, _ = field.split(".")
            sample = ".".join(sample)
            samples.add(sample)

    for condition in filters_to_flat(filters):
        key = list(condition.keys())[0]
        if key.startswith("samples"):
            _, *sample, _ = key.split(".")
            sample = ".".join(sample)
            samples.add(sample)

    return list(samples)


# def wordset_data_to_vql(wordset_expr: tuple):
#     """Get the VQL version of a Wordset expression (`(WORDSET', 'boby')`)

#     Example:

#         >>> wordset_data_to_vql(("WORDSET", "boby"))
#         "WORDSET['boby']"

#     Args:
#         wordset_expr (tuple): Tuple of 2 items: First one is "WORDSET",
#             second one is the name of the queried wordset.
#     Returns:
#         (str): Query statement
#     """
#     return "{}['{}']".format(*wordset_expr)


# def fields_to_vql(field) -> str:
#     """Return field as VQL syntax

#     This is used to convert tuple field and create a VQL query

#     Examples:
#         >>> field = ("sample", "boby", "gt")
#         >>> field_to_vql(field)
#         "sample['boby'].gt"

#     Args:
#         field(str or tuple): a Field

#     Returns:
#         str: fields for vql query
#     """
#     if isinstance(field, tuple):
#         if field[0] == GENOTYPE_FUNC_NAME and len(field) == 3:
#             return f"{field[0]}['{field[1]}'].{field[2]}"
#     # str
#     return field


# refactor


def fields_to_vql(fields) -> list:

    vql_fields = []
    for field in fields:
        if field.startswith("samples."):
            _, *name, param = field.split(".")
            name = ".".join(name)
            vql_fields.append(f"samples['{name}'].{param}")
        else:
            vql_fields.append(field)

    return vql_fields


def fields_to_sql(fields, use_as=False) -> list:
    """Return field as SQL syntax

    Args:
        field (dict): Column name from a table

    Returns:
        str: Sql field

    TODO:
        REMOVE USE_AS ?

    Examples:

        fields = {   {
            "variants": ["chr","pos","ref"]
            "annotations": ["gene","impact"],
            "samples": [
                {"name":"boby", "fields":["gt","dp"]},
                {"name":"charles", "fields":["gt"]}
                    ]
                }

    This will converted to :

    ["
    `variants`.`chr`,
    `variants`.`pos`,
    `variants`.`ref`,
    `ann`.`gene` AS ann.gene,
    `ann`.`impact` AS ann.impact,
    `sample_boby`.`gt` AS sample.boby.gt,
    `sample_boby`.`dp` AS sample.boby.dp,
    `sample_charles`.`gt` AS sample.charles.gt,
    "]


    """

    sql_fields = []

    for field in fields:

        if field.startswith("ann."):
            sql_field = f"`annotations`.`{field[4:]}`"
            if use_as:
                sql_field = f"{sql_field} AS `ann.{field[4:]}`"
            sql_fields.append(sql_field)

        elif field.startswith("samples."):
            # "sample.boby.gt"

            _, *name, value = field.split(".")

            name = ".".join(name)

            sql_field = f"`sample_{name}`.`{value}`"
            if use_as:
                sql_field = f"{sql_field} AS `samples.{name}.{value}`"
            sql_fields.append(sql_field)

        else:
            sql_fields.append(f"`variants`.`{field}`")

    return sql_fields


# refactor
def condition_to_sql(item: dict, samples=None) -> str:
    """
    Convert a key, value items from fiters into SQL query
    {"ann.gene": "CFTR"}
    Exemples:

        condition_to_sql({"chr":3}) ==> `variants`.`chr `= 3
        condition_to_sql({"chr":{"$gte": 30}}) ==> `variants`.`chr `>= 3
        condition_to_sql({"ann.gene":{"$gte": 30}}) ==> `annotation`.`gene` >= 30
        condition_to_sql({"samples.*.gt": 1 }) ==> (`samples.boby.gt = 1 AND samples.charles.gt = 1)

    """

    # TODO : optimiser
    k = list(item.keys())[0]
    v = item[k]

    if k.startswith("ann."):
        table = "annotations"
        k = k[4:]

    elif k.startswith("samples."):
        table = "samples"
        _, *name, k = k.split(".")
        name = ".".join(name)

    else:
        table = "variants"

    field = f"`{table}`.`{k}`"

    if isinstance(v, dict):
        vk, vv = list(v.items())[0]
        operator = vk
        value = vv
    else:
        operator = "$eq"
        value = v

    # MAP operator
    sql_operator = OPERATORS[operator]

    # Optimisation REGEXP
    # use LIKE IF REGEXP HAS NO special caractere
    if sql_operator == "REGEXP":
        special_caracter = "[]+.?*()^$"
        if not set(str(value)) & set(special_caracter):
            sql_operator = "LIKE"
            value = f"%{value}%"

    if sql_operator == "HAS":

        field = f"'&' || {field} || '&'"
        sql_operator = "LIKE"
        value = f"%&{value}&%"

        # WHERE '&' || consequence || '&' LIKE "%&missense_variant&%"

    # Cast value
    if isinstance(value, str):
        value = f"'{value}'"

    if isinstance(value, bool):
        value = int(value)

    # Cast IS NULL
    if value is None:
        if operator == "$eq":
            sql_operator = "IS"

        if operator == "$ne":
            sql_operator = "IS NOT"

        value = "NULL"

    # Cast wordset
    if isinstance(value, dict):
        if "$wordset" in value:
            wordset_name = value["$wordset"]
            value = f"(SELECT value FROM wordsets WHERE name = '{wordset_name}')"

    # Convert [1,2,3] =>  "(1,2,3)"
    if isinstance(value, list) or isinstance(value, tuple):
        value = (
            "("
            + ",".join([f"'{i}'" if isinstance(i, str) else f"{i}" for i in value])
            + ")"
        )

    if table == "samples":
        if name == "*" and samples:

            condition = (
                "("
                + " AND ".join(
                    [
                        f"`sample_{sample}`.`{k}` {sql_operator} {value}"
                        for sample in samples
                    ]
                )
                + ")"
            )

        else:
            condition = f"`sample_{name}`.`{k}` {sql_operator} {value}"

    else:
        condition = f"{field} {sql_operator} {value}"

    return condition


def condition_to_vql(item: dict) -> str:
    """
    Convert a key, value items from fiters into SQL query
    {"ann.gene": "CFTR"}
    Exemples:

        condition_to_sql({"chr":3}) ==> chr = 3
        condition_to_sql({"chr":{"$gte": 30}}) ==> chr >= 3
        condition_to_sql({"ann.gene":{"$gte": 30}}) ==> ann.gene >= 30

    """

    # TODO : optimiser
    k = list(item.keys())[0]
    v = item[k]

    field = k

    if isinstance(v, dict):
        vk, vv = list(v.items())[0]
        operator = vk
        value = vv
    else:
        operator = "$eq"
        value = v

    # MAP operator
    sql_operator = OPERATORS[operator]
    # hack .. we want ~ instead of REGEXP
    if sql_operator == "REGEXP":
        sql_operator = "~"

    # Cast value
    if isinstance(value, str):
        value = f"'{value}'"

    if isinstance(value, bool):
        value = int(value)

    # Cast IS NULL
    if value is None:
        if operator == "$eq":
            sql_operator = "="

        if operator == "$ne":
            sql_operator = "!="

        value = "NULL"

    # Cast wordset
    if isinstance(value, dict):
        if "$wordset" in value:
            wordset_name = value["$wordset"]
            value = f"WORDSET['{wordset_name}']"

    # Convert [1,2,3] =>  "(1,2,3)"
    if isinstance(value, list) or isinstance(value, tuple):
        value = (
            "("
            + ",".join([f"'{i}'" if isinstance(i, str) else f"{i}" for i in value])
            + ")"
        )

    if k.startswith("samples."):
        _, *name, k = k.split(".")
        name = ".".join(name)
        k = f"samples['{name}'].{k}"

        # k = f"sample{name}`.`{k}` {sql_operator} {value}"

    condition = f"{k} {sql_operator} {value}"

    return condition


def filters_to_sql(filters: dict, samples=None) -> str:
    """Build a the SQL where clause from the nested set defined in filters

    Examples:

        filters = {
            "$and": [
                {"chr": "chr1"},
                {"pos": {"$gt": 111}},
                {"$or":[
                    {"ann.gene": "CFTR"},
                    {"ann.gene": "GJB2"}
                    ]
                 }
            ]}

        where_clause = filter_to_sql(filters)
        # will output
        # variants.chr = 'chr1' AND variants.pos > 11 AND ( annotation.gene = CFTR OR annotations.gene="GJB2")

    Args:
        filters (dict): A nested set of conditions

    Returns:
        str: A sql where expression
    """
    # ---------------------------------
    def recursive(obj):

        conditions = ""
        for k, v in obj.items():
            if k in ["$and", "$or"]:
                conditions += (
                    "("
                    + f" {OPERATORS[k]} ".join([recursive(item) for item in v])
                    + ")"
                )

            else:
                conditions += condition_to_sql(obj, samples)

        return conditions

    # ---------------------------------
    query = recursive(filters)

    # hacky code to remove first level parenthesis

    return query


def filters_to_vql(filters: dict) -> str:
    """Build a the VQL where clause from the nested set defined in filters

    Examples:

        filters = {
            "$and": [
                {"chr": "chr1"},
                {"pos": {"$gt": 111}},
                {"$or":[
                    {"ann.gene": "CFTR"},
                    {"ann.gene": "GJB2"}
                    ]
                 }
            ]}

        where_clause = filter_to_sql(filters)
        # will output
        # chr = 'chr1' AND pos > 11 AND ( ann.gene = CFTR OR ann.gene="GJB2")

    Args:
        filters (dict): A nested set of conditions

    Returns:
        str: A sql where expression
    """
    # ---------------------------------
    def recursive(obj):

        conditions = ""
        for k, v in obj.items():
            if k in ["$and", "$or"]:
                conditions += (
                    "("
                    + f" {OPERATORS[k]} ".join([recursive(item) for item in v])
                    + ")"
                )

            else:
                conditions += condition_to_vql(obj)

        return conditions

    # ---------------------------------
    query = recursive(filters)

    # hacky code to remove first level parenthesis
    query = query[1:-1]

    return query


# def build_vql_query(fields, source="variants", filters={}, group_by=[], having={}):
#     """Build VQL SELECT query

#     Args:
#         fields (list): List of fields
#         source (str): source of the virtual table ( see: selection )
#         filters (dict): nested condition tree
#         group_by (list/None): list of field you want to group
#     """
#     query = "SELECT " + ",".join([fields_to_vql(i) for i in fields]) + " FROM " + source
#     if filters:
#         where_clause = filters_to_vql(filters)
#         if where_clause:
#             query += " WHERE " + where_clause

#     if group_by:
#         query += " GROUP BY " + ",".join((fields_to_vql(i) for i in group_by))

#         if having:
#             operator = having["op"]
#             value = having["value"]
#             query += f" HAVING count {operator} {value}"

#     return query


def build_sql_query(
    conn: sqlite3.Connection,
    fields,
    source="variants",
    filters={},
    order_by=None,
    order_desc=True,
    limit=50,
    offset=0,
    group_by={},
    having={},  # {"op":">", "value": 3  }
    **kwargs,
):
    """Build SQL SELECT query

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
    """

    # get samples ids

    samples_ids = {i["name"]: i["id"] for i in sql.get_samples(conn)}

    # Create fields
    sql_fields = ["`variants`.`id`"] + fields_to_sql(fields, use_as=True)

    # if group_by:
    #     sql_fields.insert(1, "COUNT() as 'count'")

    sql_query = f"SELECT DISTINCT {','.join(sql_fields)} "

    # #Add child count if grouped
    # if grouped:
    #     sql_query += ", COUNT(*) as `children`"

    # Add source table
    sql_query += "FROM variants"

    if is_annotation_join_required(fields, filters):
        sql_query += " LEFT JOIN annotations ON annotations.variant_id = variants.id"

    # Add Join Selection
    # TODO: set variants as global variables
    if source != "variants":
        sql_query += (
            " INNER JOIN selection_has_variant sv ON sv.variant_id = variants.id "
            f"INNER JOIN selections s ON s.id = sv.selection_id AND s.name = '{source}'"
        )

    ## Create Sample Join
    groupby = None

    # Test if sample*
    filters_fields = " ".join([list(i.keys())[0] for i in filters_to_flat(filters)])
    if "samples.*." in filters_fields:
        join_samples = list(samples_ids.keys())

    else:
        join_samples = samples_join_required(fields, filters)

    for sample_name in join_samples:
        if sample_name in samples_ids:
            sample_id = samples_ids[sample_name]
            sql_query += f""" INNER JOIN sample_has_variant `sample_{sample_name}` ON `sample_{sample_name}`.variant_id = variants.id AND `sample_{sample_name}`.sample_id = {sample_id}"""

    # Add Where Clause
    if filters:
        where_clause = filters_to_sql(filters, join_samples)
        if where_clause and where_clause != "()":
            sql_query += " WHERE " + where_clause

    if groupby:
        sql_query += groupby

    # # Add Group By
    # if group_by:
    #     sql_query += " GROUP BY " + ",".join(fields_to_sql(group_by, use_as=False))
    #     if having:
    #         operator = having["op"]
    #         val = having["value"]
    #         sql_query += f" HAVING count {operator} {val}"

    # Add Order By
    if order_by:
        # TODO : sqlite escape field with quote
        orientation = "DESC" if order_desc else "ASC"
        order_by = ",".join(fields_to_sql(order_by))
        sql_query += f" ORDER BY {order_by} {orientation}"

    if limit:
        sql_query += f" LIMIT {limit} OFFSET {offset}"

    return sql_query


def build_vql_query(
    fields,
    source="variants",
    filters={},
    **kwargs,
):

    select_clause = ",".join(fields_to_vql(fields))

    where_clause = filters_to_vql(filters)

    if where_clause and where_clause != "()":
        where_clause = f" WHERE {where_clause}"
    else:
        where_clause = ""

    return f"SELECT {select_clause} FROM {source}{where_clause}"
