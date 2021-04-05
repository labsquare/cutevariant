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
from cutevariant.commons import logger

LOGGER = logger()

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
    if "annotations" in fields:
        return True

    for condition in filters_to_flat(filters):
        if "$table" in condition:
            if condition["$table"] == "annotations":
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

    if "samples" in fields:
        for sample in fields["samples"].keys():
            samples.add(sample)

    for condition in filters_to_flat(filters):
        if "$table" in condition and "$name" in condition:
            samples.add(condition["$name"])
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
def fields_to_sql(fields, use_as=False) -> str:
    """Return field as SQL syntax

    Args:
        field (dict): Column name from a table

    Returns:
        str: Sql field

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
    `ann`.`gene`,
    `ann`.`impact`,
    `sample_boby`.`gt`,
    `sample_boby`.`dp`,
    `sample_charles`.`gt`,
    "]


    """

    sql_fields = []

    # extract variants
    if "variants" in fields:
        for field in fields["variants"]:
            sql_fields.append(f"`variants`.`{field}`")

    # extract annotations
    if "annotations" in fields:
        for field in fields["annotations"]:
            sql_fields.append(f"`annotations`.`{field}`")

    if "samples" in fields:
        for name, values in fields["samples"].items():
            for value in values:
                key = f"`sample_{name}`.`{value}`"
                sql_fields.append(key)

    return sql_fields


# refactor
def condition_to_sql(item: dict) -> str:
    """
    Convert a key, value items from fiters into SQL query

    Exemples:

        condition_to_sql({"chr":3}) ==> variants.chr = 3
        condition_to_sql({"chr":{"$gte": 30}}) ==> variants.chr >= 3

    """
    table = item.get("$table", "variants")

    k, v = [(i, item[i]) for i in item.keys() if i not in ("$table", "$sample")][0]

    if isinstance(v, dict):
        vk, vv = list(v.items())[0]
        operator = vk
        value = vv
    else:
        operator = "$eq"
        value = v

    # MAP operator
    sql_operator = OPERATORS[operator]

    # Cast value
    if isinstance(value, str):
        value = f"'{value}'"

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
        name = item.get("$name")
        condition = f"`sample_{name}`.`{k}` {sql_operator} {value}"

    else:
        condition = f"`{table}`.`{k}` {sql_operator} {value}"

    return condition


def filters_to_sql(filters: dict) -> str:
    """Build a the SQL where clause from the nested set defined in filters

    Examples:

        filters = {
            "$and": [
                {"chr": "chr1"},
                {"pos": {"$gt": 111}},
                {"$or":[
                    {"gene": "CFTR", "$table": "annotations"},
                    {"gene": "GJB2", "$table": "annotations"}
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

            elif k not in ("$table", "$name"):
                if k in ("annotations", "samples"):
                    for ann in v:
                        conditions += condition_to_sql(obj)
                    continue

                conditions += condition_to_sql(obj)
        return conditions

    # ---------------------------------
    query = recursive(filters)

    # hacky code to remove first level parenthesis

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
    fields,
    source="variants",
    filters={},
    order_by=None,
    order_desc=True,
    limit=50,
    offset=0,
    group_by={},
    having={},  # {"op":">", "value": 3  }
    samples_ids={},
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
        default_tables (dict): association map between fields and sql table origin
        samples_ids (dict): association map between samples name and id
    """
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
    for sample_name in samples_join_required(fields, filters):
        # Optimisation ?
        # sample_id = self.cache_samples_ids[sample_name]
        if sample_name in samples_ids:
            sample_id = samples_ids[sample_name]
            sql_query += f""" INNER JOIN sample_has_variant `sample_{sample_name}` ON `sample_{sample_name}`.variant_id = variants.id AND `sample_{sample_name}`.sample_id = {sample_id}"""

    # Add Where Clause
    if filters:
        where_clause = filters_to_sql(filters)
        if where_clause:
            sql_query += " WHERE " + where_clause

    # Add Group By
    if group_by:
        sql_query += " GROUP BY " + ",".join(fields_to_sql(group_by, use_as=False))
        if having:
            operator = having["op"]
            val = having["value"]
            sql_query += f" HAVING count {operator} {val}"

    # Add Order By
    if order_by:
        # TODO : sqlite escape field with quote
        orientation = "DESC" if order_desc else "ASC"
        order_by = ",".join(fields_to_sql(order_by))
        sql_query += f" ORDER BY {order_by} {orientation}"

    if limit:
        sql_query += f" LIMIT {limit} OFFSET {offset}"

    return sql_query


def build_full_sql_query(
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
    """Build a complete SQL SELECT statement according to the data loaded from DB

    You don't have to give the association map between fields and sql table origin
    nor the association map between samples name and id.
    In exchange SQL connection is mandatory.

    Args:
        conn (sqlite3.Connection): SQL connection
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
    # Used cached data
    default_tables, sample_ids = get_default_tables_and_sample_ids(conn)
    # LOGGER.debug(get_default_tables_and_sample_ids.cache_info())

    query = build_sql_query(
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
        samples_ids=sample_ids,
        **kwargs,
    )
    return query


@lru_cache()
def get_default_tables_and_sample_ids(conn):
    """Handy function to cache default_tables and sample_ids from database

    This function is used for every queries built in :meth:`build_full_sql_query`

    Warnings:
        Do not forget to clear this cache when samples are added in DB via
        a PED file for example.
    """
    # Get {'favorite': 'variants', 'comment': 'variants', impact': 'annotations', ...}
    default_tables = {i["name"]: i["category"] for i in sql.get_fields(conn)}
    # Get {'NORMAL': 1, 'TUMOR': 2}
    sample_ids = {i["name"]: i["id"] for i in sql.get_samples(conn)}

    return default_tables, sample_ids
