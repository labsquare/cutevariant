"""Design pattern "COMMANDS" to execute VQL query .

Each VQL statement corresponds to a <name>_cmd() fonction and is construted by
`create_command_from_obj()`.
You can use `execute(conn, vql)` or `execute_one(conn, vql)` to run a specific
VQL query.

Each command returns a JSON array with a success status code or with the
expected result.
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


def drop_cmd(conn: sqlite3.Connection, feature, name, **kwargs):
    """

    Args:
        conn (sqlite3.Connection): sqlite3 connection
        feature:
        name:

    Returns:
        dict: {"success": True}
        TODO: Use rowcount to return a non fixed success code...
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
    target,
    source="variants",
    filters=dict(),
    count=0,
    **kwargs,
):
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

    count = sql.count_query(cursor, sql_query)

    selection_id = sql.insert_selection(cursor, sql_query, name=target, count=count)

    query = f"""
    INSERT INTO selection_has_variant
    SELECT DISTINCT id, {selection_id} FROM ({sql_query})
    """

    # DROP indexes
    # For joints between selections and variants tables
    try:
        cursor.execute("""DROP INDEX idx_selection_has_variant""")
    except sqlite3.OperationalError:
        pass

    LOGGER.debug("command:create_cmd:: %s", query)
    cursor.execute(query)

    # REBUILD INDEXES
    # For joins between selections and variants tables
    sql.create_selection_has_variant_indexes(cursor)

    conn.commit()

    if cursor.rowcount:
        return {"id": cursor.lastrowid}
    return {}


def set_cmd(conn: sqlite3.Connection, target, first, second, operator, **kwargs):
    """

    Args:
        conn (sqlite3.Connection): sqlite3 connection
        target:
        first:
        second:
        operator (+, -, &): Set operators

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


def bed_cmd(conn: sqlite3.Connection, path, target, source, **kwargs):
    """

    Args:
        conn (sqlite3.Connection): sqlite3 connection
        path:
        target:
        source:

    Returns:
        (dict) with lastrowid as key id, if lines have been inserted;
        empty otherwise.
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
    """

    Args:
        conn (sqlite3.Connection): sqlite3 connection
        feature: Requested feature type of items

    Returns:
        (generator): Yield items according to requested features (fields,
        samples, selections, sets).
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

    accept_features = ("sets",)
    if feature not in accept_features:
        raise vql.VQLSyntaxError(f"option {feature} doesn't exists")

    if not os.path.isfile(path):
        raise vql.VQLSyntaxError(f"{path} doesn't exists")

    sql.insert_set_from_file(conn, name, path)
    return {"success": True}


def create_command_from_obj(conn, vql_obj: dict):
    """????

    :param conn: Sqlite3 connexion
    :param vql_obj: Requested commands: select_cmd, create_cmd, set_cmd, bed_cmd,
    show_cmd, import_cmd, drop_cmd, count_cmd
    :type conn: <sqlite3.connexion>
    :return: Function object wrapping the given vql_object.
    """
    command = vql_obj["cmd"]
    if command in globals():
        return functools.partial(globals()[command], conn, **vql_obj)


def execute(conn, vql_source: str):
    """Never used"""
    vql_obj = vql.parse_one_vql(vql_source)
    cmd = create_command_from_obj(conn, vql_obj)
    return cmd()


def execute_all(conn, vql_source: str):
    """Never used"""
    for vql in vql.parse_vql(vql_source):
        cmd = create_command_from_obj(conn, vql)
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
