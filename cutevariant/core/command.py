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
import csv

# Pip install ( because functools doesnt work with unhachable)
from memoization import cached

# Custom imports
from cutevariant.core.querybuilder import *
from cutevariant.core import sql, vql
from cutevariant.commons import logger


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
    # Get {'favorite': 'variants', 'comment': 'variants', impact': 'annotations', ...}
    default_tables = {i["name"]: i["category"] for i in sql.get_fields(conn)}
    # Get {'NORMAL': 1, 'TUMOR': 2}
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
    LOGGER.debug("command:select_cmd:: %s", query)
    for i in conn.execute(query):
        yield dict(i)


@cached(max_size=128)
def count_cmd(
    conn: sqlite3.Connection,
    fields=("chr", "pos", "ref", "alt"),
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
        dict: Count of variants with "count" as a key
    """

    if not filters:
        # Returned stored cache variant
        return {
            "count": conn.execute(
                f"SELECT count FROM selections WHERE name = '{source}'"
            ).fetchone()[0]
        }

    # Get {'favorite': 'variants', 'comment': 'variants', impact': 'annotations', ...}
    default_tables = {i["name"]: i["category"] for i in sql.get_fields(conn)}
    # Get {'NORMAL': 1, 'TUMOR': 2}
    samples_ids = {i["name"]: i["id"] for i in sql.get_samples(conn)}

    query = build_query(
        fields=fields,
        source=source,
        filters=filters,
        limit=None,
        offset=None,
        order_by=None,
        group_by=group_by,
        having=having,
        default_tables=default_tables,
        samples_ids=samples_ids,
    )
    # #    print("ICI", query, query[from_pos:])

    # print("ICI", filters)
    # if distinct:
    #     query = (
    #         "SELECT COUNT (*) FROM (SELECT DISTINCT variants.id "
    #         + query[from_pos:]
    #         + ")"
    #     )
    # else:

    query = "SELECT COUNT (*) FROM (" + query + ")"

    LOGGER.debug("command:count_cmd:: %s", query)
    return {"count": conn.execute(query).fetchone()[0]}


def drop_cmd(conn: sqlite3.Connection, feature: str, name: str, **kwargs):
    """Drop selection or set from database

    This following VQL command:
        `DROP selection boby`
    will execute :
        `drop_cmd(conn, "selections", "boby")`

    Args:
        conn (sqlite3.Connection): sqlite connection
        feature (str): selection or set
        name (str): name of the selection or the set

    Returns:
        dict: {"success": True}
        TODO: Use rowcount to return a non fixed success code...

    Raises:
        vql.VQLSyntaxError
    """
    accept_features = ["selections", "sets"]

    if feature not in accept_features:
        raise vql.VQLSyntaxError(f"{feature} doesn't exists")

    if feature == "selections":
        conn.execute(f"DELETE FROM selections WHERE name = '{name}'")
        conn.commit()
        return {"success": True}

    if feature == "sets":
        conn.execute(f"DELETE FROM sets WHERE name = '{name}'")
        conn.commit()
        return {"success": True}


def create_cmd(
    conn: sqlite3.Connection,
    target: str,
    source="variants",
    filters=dict(),
    count=0,
    **kwargs,
):
    """Create command

    This following VQL command:
        `CREATE boby FROM variants WHERE pos > 3`
    will execute :
        `create_cmd(conn, "boby", "variants", {"AND":[{"pos",">",3}]})`

    Args:
        conn (sqlite3.Connection): sqlite3 connection
        target (str): target selection table
        source (str): source selection table
        filters (TYPE): filters query
        count (int): precomputed variant count

    Returns:
        dict: {success: True}
    """
    # Get {'favorite': 'variants', 'comment': 'variants', impact': 'annotations', ...}
    default_tables = {i["name"]: i["category"] for i in sql.get_fields(conn)}
    # Get {'NORMAL': 1, 'TUMOR': 2}
    samples_ids = {i["name"]: i["id"] for i in sql.get_samples(conn)}

    if target is None:
        return {}

    # Get transaction cursor
    cursor = conn.cursor()

    sql_query = build_query(
        ["id"],
        source,
        filters,
        default_tables=default_tables,
        samples_ids=samples_ids,
        limit=None,
    )

    LOGGER.debug("command:create_cmd:: %s", sql_query)

    lastrowid = sql.create_selection_from_sql(
        conn, sql_query, target, from_selection=False
    )

    return dict() if lastrowid is None else {"id": lastrowid}


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
        (dict) with lastrowid (selection id) as key id, if lines have been
        inserted; empty otherwise.

    Examples:
        {"id": 2}: 2 lines inserted
    """
    if target is None or first is None or second is None or operator is None:
        return {}

    query_first = build_query(["id"], first, limit=None)
    query_second = build_query(["id"], second, limit=None)

    func_query = {
        "+": sql.union_variants,
        "-": sql.subtract_variants,
        "&": sql.intersect_variants,
    }

    sql_query = func_query[operator](query_first, query_second)
    LOGGER.debug("command:set_cmd:: %s", sql_query)

    lastrowid = sql.create_selection_from_sql(
        conn, sql_query, target, from_selection=False
    )

    return dict() if lastrowid is None else {"id": lastrowid}


def bed_cmd(conn: sqlite3.Connection, path: str, target: str, source: str, **kwargs):
    """Create a new selection from a bed file

    This following VQL command:
        `CREATE boby FROM variant INTERSECT "path/to/file.bed"`
    will execute :
        `bed_cmd(conn, "path/to/file.bed", "boby", "source")`

    Args:
        conn (sqlite3.Connection): sqlite3 connection
        path (str): path to bedfile ( a 3 columns files with chr, start, end )
        target (str): target selection table
        source (str): source selection table

    Returns:
        (dict) with lastrowid as key id, if lines have been inserted;
        empty otherwise.

    Raises:
        vql.VQLSyntaxError
    """
    if not os.path.isfile(path):
        raise vql.VQLSyntaxError(f"{path} doesn't exists")

    def read_bed():
        """
        Returns:
            Yields dict of bed intervals with chr, start, end, name as keys
        """
        with open(path) as file:
            reader = csv.reader(file, delimiter="\t")
            for line in reader:
                if len(line) >= 3:
                    yield {
                        "chr": line[0],
                        "start": int(line[1]),
                        "end": int(line[2]),
                        "name": "",
                    }

    # bed_intervals argument expects chr, start, end, name keys in each interval
    lastrowid = sql.create_selection_from_bed(conn, source, target, read_bed())
    return dict() if lastrowid is None else {"id": lastrowid}


def show_cmd(conn: sqlite3.Connection, feature: str, **kwargs):
    """Show command display information from a SHOW query

    This following VQL command:
        `SHOW variants`
    will execute :
        `show_cmd(conn, "variants")`

    Args:
        conn (sqlite3.Connection): sqlite3 connection
        feature (str): Requested feature type of items;
        can be: `"selections", "fields", "samples", "sets"`

    Yields:
        (generator[dict]): Items according to requested features (fields,
        samples, selections, sets).

    Raises:
        vql.VQLSyntaxError
    """
    accept_features = {
        "selections": sql.get_selections,
        "fields": sql.get_fields,
        "samples": sql.get_samples,
        "sets": sql.get_sets,
    }

    if feature not in accept_features:
        raise vql.VQLSyntaxError(f"option {feature} doesn't exists")

    for item in accept_features[feature](conn):
        yield item


def import_cmd(conn: sqlite3.Connection, feature=str, name=str, path=str, **kwargs):
    """Import command

    This following VQL command:
        `IMPORT sets "gene.txt" AS boby`
    will execute :
        `import_cmd(conn, "sets", "gene.txt")`

    Args:
        conn (sqlite3.Connection): sqlite3 connection
        feature (TYPE): "sets"
        name (TYPE): name of the set
        path (TYPE): a filepath

    Returns:
        dict: `{success: True}`

    Raises:
        vql.VQLSyntaxError
    """
    accept_features = ("sets",)

    if feature not in accept_features:
        raise vql.VQLSyntaxError(f"option {feature} doesn't exists")

    if not os.path.isfile(path):
        raise vql.VQLSyntaxError(f"{path} doesn't exists")

    sql.insert_set_from_file(conn, name, path)
    return {"success": True}


def create_command_from_obj(conn, vql_obj: dict):
    """Create command function from vql object.

    Warning:
        Use command.execute instead.

    Args:
        conn (sqlite3.Connection): sqlite3.connection
        vql_obj (dict): A VQL object with requested commands at "cmd" key:
        select_cmd, create_cmd, set_cmd, bed_cmd, show_cmd, import_cmd,
        drop_cmd, count_cmd. A VQL object is dictionary returned by vql.parse.

    Returns:
        (function): Function object wrapping the given vql_object.
    """
    command = vql_obj["cmd"]
    if command in globals():
        return functools.partial(globals()[command], conn, **vql_obj)


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
    vql_obj = vql.parse_one_vql(vql_source)
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
#         for vql_obj in vql.execute_vql(source):
#             cmd = create_command_from_vql_objet(self.conn, vql_obj)
#             self.add_command(cmd)
