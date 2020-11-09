"""Functions to build a complex SQL Select statement to query variant.

In the most of cases, you will only use build_sql_query function.

Examples::

    conn = sqlite3.Connection("::memory::")
    query = build_sql_query(["chr","pos"])
    conn.execute(query)


A variant query can be understood from the following 3 points of view.

The SQL statements:
~~~~~~~~~~~~~~~~~~~
This is the raw sqlite query::

    "SELECT `variants`.`chr`, `variants`.`pos` FROM `variants` WHERE `variants`.`ref` == 'A' "

The VQL statements:
~~~~~~~~~~~~~~~~~~~
This is a domain specific language. Check the vql module for more information::

    "SELECT chr, pos FROM variants WHERE ref == 'A'"

The Python statements:
~~~~~~~~~~~~~~~~~~~~~~
The representation of the query as a dictionnary::

    query = {
        "fields": ["chr","pos"],
        "source": "variants",
        "filters": {
        "AND":
            [
                {"name":"ref", "operator":"==","value":"A"}
            ]
        }
    }

The following module contains several functions to make easy conversion from
Python statements to VQL or SQL statements .

In the most of the case, you only need to use :

- :meth:`build_vql_query`: to create a VQL query from python statements
- :meth:`build_sql_query`: to create a SQL query from python statements
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


def fields_to_sql(field, default_tables={}, use_as=False) -> str:
    """Return field as SQL syntax

    Args:
        field (str or tuple): Column name from a table
        default_tables (dict, optional): association between field name and table origin

    Returns:
        str: Sql field

    Examples:

        >>> default_tables = {"variants.chr": "variants", "alt": "variants"}
        >>> fields_to_sql("chr", default_tables=default_tables)
        "`variants`.`chr`"
        >>> fields_to_sql("gene", default_tables=default_tables)
        "`annotations`.`gene`"
        >>> fields_to_sql("coucou", default_tables=default_tables)
        "`coucou`"
    """
    if isinstance(field, tuple):
        # If it is "genotype.name.truc then it is field function"
        # ("genotype", "boby", "gt") => `genotype_boby`.GT
        return field_function_to_sql(field, use_as)

    # extract variants.chr => (variants, chr) => `variants`.`chr`
    match = re.match(r"^(\w+)\.(\w+)", field)

    if match:
        table = match[1]
        field = match[2]
    else:
        if field in default_tables.keys():
            # Set the table
            table = default_tables[field]
        else:
            # Unknown table, just return the field
            return f"`{field}`"

    return f"`{table}`.`{field}`"


def filters_to_sql(filters, default_tables={}):
    """Return filters as SQL syntax

    Args:
        filters (dict): Nested tree of conditions
        default_tables (dict, optional): Association between field names and tables

    Returns:
        str: SQL WHERE expression

    Examples:
        >>> filters_to_sql({"AND": [("pos", ">", 34), ("af", "=", 10)})
        "`variants`.`pos` > 34 AND `variants`.`af` = 10"

    Note:
        There is a recursive function inside to parse the nested tree of conditions
    """

    def is_field(node):
        return len(node) == 3

    def recursive(node):
        if not node:
            return ""

        if is_field(node):
            # print("Node to SQL", node)
            field = fields_to_sql(node["field"], default_tables)
            value = node["value"]
            operator = node["operator"].upper()

            if operator == "~":
                operator = "REGEXP"

            if operator in ("IN", "NOT IN") and isinstance(value, str):
                # node: {'field': 'ref', 'operator': 'IN', 'value': "('A', 'T', 'G', 'C')"}
                # wanted: "ref IN ('A', 'T', 'G', 'C')"
                # Try to cast string to tuple
                try:
                    temp_val = literal_eval(value)
                    value = temp_val
                except ValueError:
                    pass

            elif isinstance(value, str):
                # enclose string with quotes
                value = f"'{value}'"

            if isinstance(value, tuple):
                # If value is a WORDSET["salut"] aka ('WORDSET', 'salut')
                # => Get SQL statement
                if value[0] == WORDSET_FUNC_NAME:
                    value = wordset_data_to_sql(value)
                elif len(value) == 1:
                    # Remove trailing comma in tuple with 1 element ("xxx",)
                    value = str(value).replace(",", "")

            # Strings must be space separated because of operators (IN, etc.)
            return "%s %s %s" % (field, operator, value)

        # If node is not a field: 1 key only: the logical operator
        logic_op = list(node.keys())[0]
        g = (recursive(child) for child in node[logic_op])
        out = [sql_filter for sql_filter in g if sql_filter]
        # print("to SQL", out, "LOGIC", logic_op)
        # Recursive call for each field in the list associated to the
        # logical operator.
        # node:
        # {'AND': [
        #   {'field': 'ref', 'operator': 'IN', 'value': "('A', 'T', 'G', 'C')"},
        #   {'field': 'alt', 'operator': 'IN', 'value': "('A', 'T', 'G', 'C')"}
        # ]}
        # Wanted: "ref IN ('A', 'T', 'G', 'C') AND alt IN ('A', 'T', 'G', 'C')"
        # to SQL ["ref IN ('A', 'T', 'G', 'C')", "alt IN ('A', 'T', 'G', 'C')"]
        if not out:
            return ""
        if len(out) == 1:
            return out[0]
        return "(" + f" {logic_op} ".join(out) + ")"

    return recursive(filters)


def filters_to_vql(filters):
    """Return filters as VQL syntax

    Args:
        filters (dict): Nested tree of conditions

    Returns:
        str: VQL WHERE expression
    """

    def is_field(node):
        return len(node) == 3

    def recursive(node):
        if not node:
            return ""

        if is_field(node):
            # print("Node to VQL", node)
            field = fields_to_vql(node["field"])
            value = node["value"]
            operator = node["operator"].upper()

            if operator in ("IN", "NOT IN") and isinstance(value, str):
                # node: {'field': 'ref', 'operator': 'IN', 'value': "('A', 'T', 'G', 'C')"}
                # wanted: "ref IN ('A', 'T', 'G', 'C')"
                # Try to cast string to tuple
                try:
                    temp_val = literal_eval(value)
                    value = temp_val
                except ValueError:
                    pass

            elif isinstance(value, str):
                value = f"'{value}'"

            if isinstance(value, tuple):
                # If value is ('WORDSET', 'salut') aka WORDSET["salut"]
                # => Get VQL statement
                if len(value) == 2 and value[0] == WORDSET_FUNC_NAME:
                    value = wordset_data_to_vql(value)
                elif len(value) == 1:
                    # Remove trailing comma in tuple with 1 element ("xxx",)
                    value = str(value).replace(",", "")

            # Strings must be space separated because of operators (IN, etc.)
            return "%s %s %s" % (field, operator, value)

        # If node is not a field: 1 key only: the logical operator
        logic_op = list(node.keys())[0]
        g = (recursive(child) for child in node[logic_op])
        out = [sql_filter for sql_filter in g if sql_filter]
        # print("to VQL", out, "LOGIC", logic_op)
        # {'field': 'chr', 'operator': 'IN', 'value': (10.0, 11.0)}
        # to VQL ['chr IN (10.0, 11.0)'] LOGIC AND
        if not out:
            return ""
        if len(out) == 1:
            return out[0]
        return "(" + f" {logic_op} ".join(out) + ")"

    # Do not return first level of enclosing parenthesis
    vql_filters = recursive(filters)
    if vql_filters.startswith("("):
        return vql_filters[1:-1]
    return vql_filters


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
