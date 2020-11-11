"""Design pattern "COMMANDS" to execute VQL query .

Each VQL statement corresponds to a <name>_cmd() function.
You can use `execute(conn, vql)` or `execute_all(conn, vql)` to run a specific
VQL query.

Each command returns a JSON array with a success status code or with the
expected result.

Command module is usefull for CLI and for running VQL scripts.

Example:

    >>> conn = sqlite.Connection("project.db")
    >>> for variant in execute(conn, "SELECT chr, pos FROM variants"):
    ...     print(variant)
    >>> # How many variants ?
    >>> print(execute(conn, "COUNT FROM variants"))
"""
# Standard imports
import sqlite3
import os
import functools

# Pip install ( because functools doesnt work with unhachable)
from memoization import cached

# Custom imports
from cutevariant.core.querybuilder import build_sql_query, build_full_sql_query
from cutevariant.core import sql, vql
from cutevariant.commons import logger
from cutevariant.core.reader import BedReader

LOGGER = logger()


def select_cmd(
    conn: sqlite3.Connection,
    fields=("chr", "pos", "ref", "alt"),
    source="variants",
    filters={},
    order_by=None,
    order_desc=True,
    group_by=[],
    having={},  # {"op":">", "value": 3  }
    limit=50,
    offset=0,
    **kwargs,
):
    """Select query Command

    This following VQL command:
        `SELECT chr,pos FROM variants WHERE pos > 3`
    will execute :
        `select_cmd(conn, ["chr", "pos"], variants", {"AND": [{"pos","=",3}]}))`

    Args:
        conn (sqlite3.Connection): sqlite3 connection
        fields (list, optional): list of fields
        filters (dict, optional): nested tree of condition
        source (str, optional): virtual table source
        order_by (list, optional): order by field name
        order_desc (bool, optional): Descending or Ascending Order
        limit (int, optional): record count
        offset (int, optional): record count per page

    Yields:
        variants (dict)
    """
    query = build_full_sql_query(
        conn,
        fields=fields,
        source=source,
        filters=filters,
        order_by=order_by,
        order_desc=order_desc,
        limit=limit,
        offset=offset,
        group_by=group_by,
        having=having,
        **kwargs,
    )
    LOGGER.debug("command:select_cmd:: %s", query)
    for i in conn.execute(query):
        # THIS IS INSANE... SQLITE DOESNT RETURN ALIAS NAME WITH SQUARE BRACKET....
        # I HAVE TO replace [] by () and go back after...
        # TODO : Change VQL Syntax from [] to () would be a good alternative
        # @See QUERYBUILDER
        # See : https://stackoverflow.com/questions/41538952/issue-cursor-description-never-returns-square-bracket-in-column-name-python-2-7-sqlite3-alias
        yield {k.replace("(", "[").replace(")", "]"): v for k, v in dict(i).items()}


@cached(max_size=128)
def count_cmd(
    conn: sqlite3.Connection,
    fields=["chr", "pos", "ref", "alt"],
    source="variants",
    filters={},
    group_by=[],
    having={},
    **kwargs,
):
    """Count command

    This following VQL command:
        `COUNT FROM variants WHERE pos > 3`
    will execute :
        `count_cmd(conn, "variants", {"AND": [{"pos","=",3}]}))`

    Args:
        conn (sqlite3.Connection): sqlite3 connection
        source (str, optional): virtual source table
        filters (dict, optional): nested tree of condition

    Returns:
        dict: Count of variants wgstith "count" as a key
    """
    # See #177: Check if fields has annotations
    # If an annotation field is selected, the variant count stored in the selection
    # table (count without taking account of annotations) is different.
    # This leads to a fault in the pagination hiding the latest variants if
    # more than 50 must be displayed.
    variants_fields = set(field["name"] for field in sql.get_field_by_category(conn, "variants"))

    if set(fields).issubset(variants_fields) and not filters and not group_by:
        # All fields are in variants table
        # Returned stored cache variant
        LOGGER.debug("command:count_cmd:: cached from selections table")
        return {
            "count": conn.execute(
                f"SELECT count FROM selections WHERE name = '{source}'"
            ).fetchone()[0]
        }

    query = build_full_sql_query(
        conn,
        fields=fields,
        source=source,
        filters=filters,
        limit=None,
        offset=None,
        order_by=None,
        group_by=group_by,
        having=having,
        **kwargs,
    )

    # THIS IS INSANE... SQLITE DOESNT RETURN ALIAS NAME WITH SQUARE BRACKET....
    # I HAVE TO replace [] by () and go back after...
    # TODO : Change VQL Syntax from [] to () would be a good alternative
    # @See QUERYBUILDER
    # See : https://stackoverflow.com/questions/41538952/issue-cursor-description-never-returns-square-bracket-in-column-name-python-2-7-sqlite3-alias
    LOGGER.debug("command:count_cmd:: %s", query)
    return {"count": sql.count_query(conn, query)}


def drop_cmd(conn: sqlite3.Connection, feature: str, name: str, **kwargs):
    """Drop selection or set from database

    This following VQL commands::

        DROP selections boby
        DROP wordsets mygene

    will execute::

        drop_cmd(conn, "selections", "boby")
        drop_cmd(conn, "wordsets", "boby")

    Args:
        conn (sqlite3.Connection): sqlite connection
        feature (str): selections or wordsets (Names of the SQL tables).
            Lower case features are also accepted.
        name (str): name of the selection or name of the wordset

    Returns:
        dict: {"success": <boolean>}; True if deletion is ok, False otherwise.

    Raises:
        vql.VQLSyntaxError
    """
    accept_features = ("selections", "wordsets")

    # Cast to lower case
    feature = feature.lower()

    if feature not in accept_features:
        raise vql.VQLSyntaxError(f"{feature} doesn't exists")

    affected_lines = sql.delete_by_name(conn, name, table_name=feature)
    return {"success": (affected_lines > 0)}


def create_cmd(
    conn: sqlite3.Connection,
    target: str,
    source="variants",
    filters=dict(),
    count=None,
    **kwargs,
):
    """Create a selection from the given source, filtered by filters

    This following VQL command:
        `CREATE boby FROM variants WHERE pos > 3`
    will execute :
        `create_cmd(conn, "boby", "variants", {"AND":[{"pos",">",3}]})`

    Args:
        conn (sqlite3.Connection): sqlite3 connection
        target (str): target selection name
        source (str): source selection name
        filters (dict): filters used to select the variants from source
        count (int): precomputed variant count

    Returns:
        dict: {"id": selection_id} if lines have been inserted,
            or empty dict in case of error
    """
    if target is None:
        return {}

    sql_query = build_full_sql_query(
        conn,
        fields=["id"],
        source=source,
        filters=filters,
        limit=None,
        **kwargs,
    )

    LOGGER.debug("command:create_cmd:: %s", sql_query)
    selection_id = sql.create_selection_from_sql(
        conn, sql_query, target, count=count, from_selection=False
    )
    return dict() if selection_id is None else {"id": selection_id}


def set_cmd(
    conn: sqlite3.Connection, target: str, first: str, second: str, operator, **kwargs
):
    """Perform set operation like intersection, union and difference between two table selection

    This following VQL command:
        `CREATE boby = raymond & charles`
    will execute :
        `set_cmd(conn, "boby", "raymond", "charles", "&")`

    Args:
        conn (sqlite3.Connection): sqlite3 connection
        target (str): table selection target
        first (str): first selection in operation
        second (str): second selection in operation
        operator (str): + (union), - (difference), & (intersection) Set operators

    Returns:
        dict: {"id": selection_id} if lines have been inserted,
            or empty dict in case of error

    Examples:
        {"id": 2}: 2 lines inserted
    """
    if target is None or first is None or second is None or operator is None:
        return {}

    query_first = build_sql_query(["id"], first, limit=None)
    query_second = build_sql_query(["id"], second, limit=None)

    func_query = {
        "|": sql.union_variants,
        "-": sql.subtract_variants,
        "&": sql.intersect_variants,
    }

    sql_query = func_query[operator](query_first, query_second)
    LOGGER.debug("command:set_cmd:: %s", sql_query)

    selection_id = sql.create_selection_from_sql(
        conn, sql_query, target, from_selection=False
    )
    return dict() if selection_id is None else {"id": selection_id}


def bed_cmd(conn: sqlite3.Connection, path: str, target: str, source: str, **kwargs):
    """Create a new selection from a bed file

    This following VQL command:
        `CREATE boby FROM variants INTERSECT "path/to/file.bed"`
    will execute :
        `bed_cmd(conn, "path/to/file.bed", "boby", "source")`

    Args:
        conn (sqlite3.Connection): sqlite3 connection
        path (str): path to bedfile ( a 3 columns files with chr, start, end )
        target (str): target selection table
        source (str): source selection table

    Returns:
        dict: {"id": id of last line inserted} if lines have been inserted,
            or empty dict in case of error

    Raises:
        vql.VQLSyntaxError
    """
    if not os.path.isfile(path):
        raise vql.VQLSyntaxError(f"{path} doesn't exists")

    # bed_intervals: chrom, start, end, name, etc. keys in each interval
    # see also cutevariant/core/reader/bedreader.py
    selection_id = sql.create_selection_from_bed(conn, source, target, BedReader(path))
    return dict() if selection_id is None else {"id": selection_id}


def show_cmd(conn: sqlite3.Connection, feature: str, **kwargs):
    """Show command display information from a SHOW query

    This following VQL command:
        `SHOW variants`
    will execute :
        `show_cmd(conn, "variants")`

    Args:
        conn (sqlite3.Connection): sqlite3 connection
        feature (str): Requested feature type of items (Name of the SQL table);
            Lower case features are also accepted.
        can be: `"selections", "fields", "samples", "wordsets"`

    Yields:
        (generator[dict]): Items according to requested feature.

    Raises:
        vql.VQLSyntaxError
    """
    accepted_features = {
        "selections": sql.get_selections,
        "fields": sql.get_fields,
        "samples": sql.get_samples,
        "wordsets": sql.get_wordsets,
    }

    # Cast in lower case
    feature = feature.lower()

    if feature not in accepted_features:
        raise vql.VQLSyntaxError(f"option {feature} doesn't exists")

    for item in accepted_features[feature](conn):
        yield item


def import_cmd(conn: sqlite3.Connection, feature=str, name=str, path=str, **kwargs):
    """Import command for wordsets only

    This following VQL command:
        `IMPORT WORDSETS "gene.txt" AS boby`
    will execute :
        `import_cmd(conn, "WORDSETS", "gene.txt")`

    Args:
        conn (sqlite3.Connection): sqlite3 connection
        feature (str): "WORDSETS" (Name of the SQL table)
        name (str): name of the set
        path (str): a filepath

    Returns:
        dict: `{success: <boolean>}`

    Raises:
        vql.VQLSyntaxError
    """
    accepted_features = ("wordsets",)

    if feature.lower() not in accepted_features:
        raise vql.VQLSyntaxError(f"option {feature} doesn't exists")

    if not os.path.isfile(path):
        raise vql.VQLSyntaxError(f"{path} doesn't exists")

    affected_rows = sql.import_wordset_from_file(conn, name, path)
    return {"success": (affected_rows is not None)}


def create_command_from_obj(conn, vql_obj: dict):
    """Create command function from vql object according to its "cmd" key

    cmd authorized:

        - select_cmd
        - count_cmd
        - drop_cmd
        - create_cmd
        - set_cmd
        - bed_cmd
        - show_cmd
        - import_cmd

    Warning:
        Use :meth:`execute` instead, that is a wrapper to this function.

    Examples:
        If you want to create a select_cmd function, pass a vql_obj like this one:

        .. code-block:: python

            {
                "cmd": "select_cmd",
                "fields": ["chr", "pos"],
                "source": "variants",
                "filters": {},
            }

    Args:
        conn (sqlite3.Connection): sqlite3.connection
        vql_obj (dict): A VQL object with requested commands at "cmd" key:
            `select_cmd, create_cmd, set_cmd, bed_cmd, show_cmd, import_cmd,
            drop_cmd, count_cmd`.
            A VQL object is dictionary returned by vql.parse.

    Returns:
        (function): Function object wrapping the given vql_object.
    """
    command = vql_obj["cmd"]
    if command in globals():
        return functools.partial(globals()[command], conn, **vql_obj)
    raise vql.VQLSyntaxError(f"cmd {command} doesn't exists")


def execute(conn: sqlite3.Connection, vql_source: str):
    """Execute a vql query

    Examples:
        >>> for variant in execute(conn,"SELECT chr from variants"):
        >>>     print(variant)

    Args:
        conn (sqlite3.Connection): sqlite3 connection
        vql_source (str): a VQL query

    Returns:
        dict: Return command output as a dict
    """
    # Convert VQL string into VQL object
    vql_obj = vql.parse_one_vql(vql_source)
    # Convert VQL object into wrapped SQL query
    cmd = create_command_from_obj(conn, vql_obj)
    return cmd()


def execute_all(conn: sqlite3.Connection, vql_source: str):
    """Execute a vql script

    Examples:
        >>> execute_all(
        ...     "CREATE boby FROM variants; CREATE raymon FROM variants;"
        ...     "CREATE charles = boby - variants; COUNT(charles)"
        ... )

    Args:
        conn (sqlite3.Connection): sqlite3 connection
        vql_source (str): a VQL query

    Yields:
        (generator[dict]): Yield command outputs as a dicts
    """
    for vql_obj in vql.parse_vql(vql_source):
        cmd = create_command_from_obj(conn, vql_obj)
        yield cmd()


def clear_cache_cmd():
    """Clear function cache by memoization module.

    This method must be called when new project is open
    """
    count_cmd.cache_clear()


# class CommandGraph(object):
#     def __init__(self, conn):
#         super().__init__()
#         self.conn = conn
#         self.graph = nx.DiGraph()
#         self.graph.add_node("variants")

#     def add_command(self, command: Command):

#         if type(command) == CreateCommand:
#             self.graph.add_node(command.target)
#             self.graph.add_edge(command.source, command.target)

#         if type(command) == SelectCommand:
#             self.graph.add_node("Select")
#             self.graph.add_edge(command.source, "Select")

#         if type(command) == SetCommand:
#             self.graph.add_node(command.target)
#             self.graph.add_edge(command.first, command.target)
#             self.graph.add_edge(command.second, command.target)

#     def set_source(self, source):
#         self.graph.clear()
#         for vql_obj in vql.parse_vql(source):
#             cmd = create_command_from_vql_objet(self.conn, vql_obj)
#             self.add_command(cmd)
