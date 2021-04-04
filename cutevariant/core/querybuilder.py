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
GENOTYPE_FUNC_NAME = "sample"
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
    "$regex": "REXP",
    "$and": "AND",
    "$or": "OR",
}


def filters_to_flat(filters: dict):
    """Recursive function to convert the filter hierarchical dictionnary into a list of fields

    Args:
        filters (dict): a nested tree of condition. @See example

    Returns:
        (list): all fields are now inside a a list

    .. todo:: Move to vql ?

    Examples::

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
            # length = 3 to skip AND/OR levels
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

        >>> # which correspond to genotype(boby).GT in VQL
        >>> field = ("genotype", "boby", "gt")
        >>> field_function_to_sql(field)
        "`genotype_boby`.`gt`"
    """
    func_name, arg_name, field_name = field_function

    if use_as:
        # THIS IS INSANE... SQLITE DOESNT RETURN ALIAS NAME WITH SQUARE BRACKET....
        # I HAVE TO replace [] by () and go back after...
        # TODO : Change VQL Syntax from [] to () would be a good alternative
        # See : https://stackoverflow.com/questions/41538952/issue-cursor-description-never-returns-square-bracket-in-column-name-python-2-7-sqlite3-alias
        alias_name = fields_to_vql(field_function).replace("[", "(").replace("]", ")")
        suffix = ' AS "{}"'.format(alias_name)
    else:
        suffix = ""

    if field_name:
        return f"`{func_name}_{arg_name}`.`{field_name}`" + suffix
    return f"`{func_name}_{arg_name}`" + suffix


def wordset_data_to_sql(wordset_expr: tuple):
    """Get the SQL version of a Wordset expression (`(WORDSET', 'boby')`)

    Wordset function is used in VQL to filter fields within a set of words.

    Example:

        .. code-block:: sql

            SELECT ... WHERE gene IN WORDSET('boby')
            -- will be replaced by:
            SELECT ... WHERE gene IN (SELECT value FROM sets WHERE name = 'boby')

        We return only the sub SELECT statement here::

            >>> wordset_data_to_sql(("WORDSET", "boby"))
            "SELECT value FROM sets WHERE name = 'boby'"

    Args:
        wordset_expr (tuple): Tuple of 2 items: First one is "WORDSET",
            second one is the name of the queried wordset.
    Returns:
        (str): Query statement
    """
    func_name, arg_name = wordset_expr
    assert func_name == WORDSET_FUNC_NAME
    return f"(SELECT value FROM wordsets WHERE name = '{arg_name}')"


def wordset_data_to_vql(wordset_expr: tuple):
    """Get the VQL version of a Wordset expression (`(WORDSET', 'boby')`)

    Example:

        >>> wordset_data_to_vql(("WORDSET", "boby"))
        "WORDSET['boby']"

    Args:
        wordset_expr (tuple): Tuple of 2 items: First one is "WORDSET",
            second one is the name of the queried wordset.
    Returns:
        (str): Query statement
    """
    return "{}['{}']".format(*wordset_expr)


def fields_to_vql(field) -> str:
    """Return field as VQL syntax

    This is used to convert tuple field and create a VQL query

    Examples:
        >>> field = ("sample", "boby", "gt")
        >>> field_to_vql(field)
        "sample['boby'].gt"

    Args:
        field(str or tuple): a Field

    Returns:
        str: fields for vql query
    """
    if isinstance(field, tuple):
        if field[0] == GENOTYPE_FUNC_NAME and len(field) == 3:
            return f"{field[0]}['{field[1]}'].{field[2]}"
    # str
    return field


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
def condition_to_sql(item):
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
        condition = f"`{table}_{name}`.`{k}` {sql_operator} {value}"

    else:
        condition = f"`{table}`.`{k}` {sql_operator} {value}"

    return condition


def filters_to_sql(filters):

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


def build_vql_query(fields, source="variants", filters={}, group_by=[], having={}):
    """Build VQL SELECT query

    Args:
        fields (list): List of fields
        source (str): source of the virtual table ( see: selection )
        filters (dict): nested condition tree
        group_by (list/None): list of field you want to group
    """
    query = "SELECT " + ",".join([fields_to_vql(i) for i in fields]) + " FROM " + source
    if filters:
        where_clause = filters_to_vql(filters)
        if where_clause:
            query += " WHERE " + where_clause

    if group_by:
        query += " GROUP BY " + ",".join((fields_to_vql(i) for i in group_by))

        if having:
            operator = having["op"]
            value = having["value"]
            query += f" HAVING count {operator} {value}"

    return query


def build_sql_query(
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
    fields_in_filters = {i["field"] for i in filters_to_flat(filters)}

    # Loop over fields and check is annotations is required
    annotation_fields = {i for i, v in default_tables.items() if v == "annotations"}

    need_join_annotations = False
    for col in set(sql_fields) | fields_in_filters:
        # Example of field:
        # '`annotations`.`gene`'
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
    ## detect if fields contains function like (genotype,boby,gt) and save boby
    all_fields = set(fields_in_filters)
    all_fields.update(fields)

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
        if where_clause:
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
