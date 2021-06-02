"""
The SQL module is part of cutevariant's bakcbone.
A cutevariant project is basically a sqlite3 database, and this module's goal is to provide a set of useful functions to access it.
In this module, you will find a collection of functions that execute SQL requests to easily manipulate cutevariant's database.

Every function in this module is responsible for **one** CRUD operation, and is always named with the following prefixes: 

- `create_`

- `remove_`

- `update_`,`insert_`

- `get_`

They all take a Sqlite3 connection as a parameter, called `conn` (except for `get_sql_connection` that actually returns one)

The module also contains a QueryBuilder class to build complex variant query based on filters, columns and selections.

If you don't find the request you need, please open an issue on [our github repository](https://github.com/labsquare/cutevariant/issues)

Example:
    ```python
    # Read sample table information
    from cutevariant.core import sql
    conn = sql.get_sql_connection("project.db")
    sql.get_samples(conn)

    # Build a variant query
    from cutevariant.core import sql
    conn = sql.get_sql_connection("project.db")
    builder = QueryBuilder(conn)
    builder.columns = ["chr","pos","ref","alt"]
    print(builder.sql())
    ```

"""

# Standard imports
import sqlite3
from collections import defaultdict
import re
import logging

# from typing_extensions import TypeAlias
from pkg_resources import parse_version
from functools import partial, lru_cache
import itertools as it
import numpy as np
from typing import Any, Generator, Tuple, List, Union, Iterable, Set


# Custom imports
import cutevariant.commons as cm
from cutevariant.core import querybuilder
from cutevariant.core.querybuilder import build_sql_query

# from cutevariant.core.sql_aggregator import StdevFunc

LOGGER = cm.logger()


def get_sql_connection(filepath: str) -> sqlite3.Connection:
    """Opens a SQLite database and returns the connection object

    Args:
        filepath (str): sqlite3 database filepath

    Returns:
        The connection is initialized with `row_factory = Row`.
        So all results are accessible via indexes or keys.
        The returned connection also adds support for custom functions:
        - REGEXP function.
            Usage: REGEXP(pattern,tested_string). Returns true iff tested_string matches regex pattern.
    """
    connection = sqlite3.connect(filepath)
    # Activate Foreign keys
    connection.execute("PRAGMA foreign_keys = ON")
    connection.row_factory = sqlite3.Row
    foreign_keys_status = connection.execute("PRAGMA foreign_keys").fetchone()[0]
    LOGGER.debug("get_sql_connection:: foreign_keys state: %s", foreign_keys_status)
    assert foreign_keys_status == 1, "Foreign keys can't be activated :("

    # Create function for SQLite
    def regexp(expr, item):
        # Need to cast item to str... costly
        return re.search(expr, str(item)) is not None

    connection.create_function("REGEXP", 2, regexp)
    # connection.create_aggregate("STD", 1, StdevFunc)

    if LOGGER.getEffectiveLevel() == logging.DEBUG:
        # Enable tracebacks from custom functions in DEBUG mode only
        sqlite3.enable_callback_tracebacks(True)

    return connection


def get_database_file_name(conn: sqlite3.Connection) -> str:
    """Returns the file name that conn is connected to

    Args:
        conn (sqlite3.Connection): The Sqlite3 connection you'd like to have the file name of

    Returns:
        The file name conn is connected to
    """
    return conn.execute("PRAGMA database_list").fetchone()["file"]


def table_exists(conn: sqlite3.Connection, name: str) -> bool:
    """Returns True if table exists in the database

    Args:
        conn (sqlite3.Connection): Sqlite3 connection to a database
        name (str): Table name you're looking for in the database that conn is connected to

    Returns:
        True if table exists
    """
    c = conn.cursor()
    c.execute(f"SELECT name FROM sqlite_master WHERE name = '{name}'")
    return c.fetchone() != None


def drop_table(conn: sqlite3.Connection, table_name: str):
    """Drop the given table

    Args:
        conn (sqlite3.Connection): Sqlite3 connection
        table_name (str): Name of the table to drop
    """
    cursor = conn.cursor()
    cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
    conn.commit()


def clear_table(conn: sqlite3.Connection, table_name: str):
    """Clear content of the given table

    Args:
        conn (sqlite3.Connection): Sqlite3 connection
        table_name (str): Name of the table to clear
    """
    cursor = conn.cursor()
    cursor.execute(f"DELETE  FROM {table_name}")
    conn.commit()


def get_table_columns(conn: sqlite3.Connection, table_name: str) -> List[str]:
    """Returns the list of columns for the given table

    Args:
        conn (sqlite3.Connection): Sqlite3 connection
        table_name (str): The table you want the column names of

    Returns:
        List of column names in table table_name.

    !!! example

        ```python
        >>> sql.get_table_columns(conn,"fields")
        >>> ['name', 'category', 'type', 'description']
        ```

    References:
        used by async_insert_many_variants() to build queries with placeholders
    """
    return [
        c[1] for c in conn.execute(f"pragma table_info({table_name})") if c[1] != "id"
    ]


def create_indexes(conn: sqlite3.Connection):
    """Create extra indexes on tables

    Args:
        conn (sqlite3.Connection): Sqlite3 connection

    Note:
        This function must be called after batch insertions.
        You should use this function instead of individual functions.

    """
    create_variants_indexes(conn)
    create_selections_indexes(conn)

    try:
        # Some databases have not annotations table
        create_annotations_indexes(conn)
    except sqlite3.OperationalError as e:
        LOGGER.debug("create_indexes:: sqlite3.%s: %s", e.__class__.__name__, str(e))


def count_query(conn: sqlite3.Connection, query: str) -> int:
    """Count elements from the given query or table

    Args:
        conn (sqlite3.Connection): Sqlite3 connection
        query (str): SQL query you want to have the line count of

    Returns:
        Number of lines returned by the query
    """
    return conn.execute(f"SELECT COUNT(*) as count FROM ({query})").fetchone()[0]


# Statistical data. TODO: these functions are not usable for now. They work with the stats plugin which is still under development

# WORK IN PROGRESS
def get_stats_info(conn, field, source="variants", filters={}):
    pass


# WORK IN PROGRESS
def get_field_info(conn, field, source="variants", filters={}, metrics=["mean", "std"]):
    """
    Returns statistical metrics for column field in conn
    metrics is the list of statistical metrics you'd like to retrieve, among:
    count,mean,std,min,q1,median,q3,max

    For the metrics, you can also specify your own as a tuple by following the following format:

    (metric_name,callable) where callable takes a numpy array and metric_name will be the key in the result
    dictionnary. Example:

    ("standard error",lambda array:np.std(array)/np.sqrt(len(array)))

    The returned dict is in the form:
    {
        "mean" : 42,
        "min" : 5,
        "max" : 1000
        "arbitrary_metric":15
    }
    It WILL and SHOULD change in the future
    """

    # metrics are literals, not column names, so add some single quotes to tell SQL

    # TODO :

    metric_functions = {
        "count": len,
        "mean": np.mean,
        "std": np.std,
        "min": lambda ar: np.quantile(ar, 0.0),
        "q1": lambda ar: np.quantile(ar, 0.25),
        "median": lambda ar: np.quantile(ar, 0.5),
        "q3": lambda ar: np.quantile(ar, 0.75),
        "max": lambda ar: np.quantile(ar, 1.0),
    }

    conn.row_factory = None
    query = build_sql_query(conn, [field], source, filters, limit=None)

    data = [i[0] for i in conn.execute(query)]

    results = {}
    for metric in metrics:
        if metric in metric_functions:
            value = metric_functions[metric](data)
            results[metric] = value

        if isinstance(metric, tuple) and len(metric) == 2:
            metric_name, metric_func = metric
            if callable(metric_func):
                value = metric_func(data)
                results[metric_name] = value

    conn.row_factory = sqlite3.Row

    return results


## project table ===============================================================


def create_table_project(conn: sqlite3.Connection, name: str, reference: str):
    """Creates the table "projects" and inserts project name and reference genome

    Args:
        conn (sqlite3.Connection): Sqlite3 connection
        name (str): Project name
        reference (str): Reference genom for this project

    """
    project_data = {"name": name, "reference": reference}

    conn.execute("CREATE TABLE projects (id INTEGER PRIMARY KEY, key TEXT, value TEXT)")
    conn.commit()

    update_project(conn, project_data)


def update_project(conn: sqlite3.Connection, project: dict):
    """Writes key,value pairs from project into the table 'projects', represented by sqlite3 connection conn

    Args:
        conn (sqlite3.Connection): Sqlite3 connection to a database with the table 'projects' you want to update
        project (dict): Collection of key,value pairs you want to insert into the table 'projects'
    """
    conn.executemany(
        "INSERT INTO projects (key, value) VALUES (?, ?)", list(project.items())
    )
    conn.commit()


def get_project(conn: sqlite3.Connection) -> dict:
    """Returns a python dict where each key, value pair is one line of the table 'projects' defined in sqlite3 connection conn.

    Args:
        conn (sqlite3.Connection): Sqlite3 connection with table 'projects'

    Returns:
        A  python dict where key,value pairs are one line of the table 'projects'
    """
    g = (dict(data) for data in conn.execute("SELECT key, value FROM projects"))
    return {data["key"]: data["value"] for data in g}


## metadatas table =============================================================


def create_table_metadatas(conn: sqlite3.Connection):
    """Creates 'metadata' table in database that conn is connected to

    Args:
        conn (sqlite3.Connection): Sqlite3 connection
    """
    conn.execute(
        "CREATE TABLE metadatas (id INTEGER PRIMARY KEY, key TEXT, value TEXT)"
    )


def insert_many_metadatas(conn: sqlite3.Connection, metadatas: dict = {}):
    """Inserts key,value pairs from dict metadatas, into the table 'metadatas' of database represented by conn

    Args:
        conn (sqlite3.Connection): Sqlite3 connection
        metadatas (dict, optional): Collection of key,value pairs to insert into the table 'metadatas'. Defaults to {}.
    """
    if metadatas:
        cursor = conn.cursor()
        cursor.executemany(
            "INSERT INTO metadatas (key,value) VALUES (?,?)", list(metadatas.items())
        )

        conn.commit()


def get_metadatas(conn: sqlite3.Connection) -> dict:
    """Returns a dictionary of metadatas

    Returns:
        A python dict where each key,value pair represents metadata that was inserted in the 'metadatas' table
    """
    conn.row_factory = sqlite3.Row
    g = (dict(data) for data in conn.execute("SELECT key, value FROM metadatas"))
    return {data["key"]: data["value"] for data in g}


## selections & sets tables ====================================================


def delete_by_name(conn: sqlite3.Connection, name: str, table_name: str = None) -> int:
    """Delete data in "selections" or "sets" tables with the given name

    Args:
        conn (sqlit3.Connection): Sqlite3 connection
        name (str): Selection/set name
        table_name (str): Name of the table concerned by the deletion
    Returns:
        Number of rows affected
    """
    if table_name is None:
        raise ValueError("Please specify a table name")

    if table_name == "selections" and name == "variants":
        LOGGER.error("Cannot remove the default selection 'variants'")
        return

    cursor = conn.cursor()
    cursor.execute(f"DELETE FROM `{table_name}` WHERE name = ?", (name,))
    conn.commit()
    return cursor.rowcount


## selection table =============================================================


def create_table_selections(conn: sqlite3.Connection):
    """Creates tables "selections" and association table "selection_has_variant"

    This table stores variants selection saved by the user:

        - name: name of the set of variants
        - count: number of variants concerned by this set
        - query: the SQL query which generated the set

    Args:
        conn (sqlite3.Connection): Sqlite3 Connection
    """
    cursor = conn.cursor()
    # selection_id is an alias on internal autoincremented 'rowid'
    cursor.execute(
        """CREATE TABLE selections (
        id INTEGER PRIMARY KEY ASC,
        name TEXT, count INTEGER, query TEXT
        )"""
    )

    # Association table: do not use useless rowid column
    cursor.execute(
        """CREATE TABLE selection_has_variant (
        variant_id INTEGER NOT NULL,
        selection_id INTEGER NOT NULL,
        PRIMARY KEY (variant_id, selection_id),
        FOREIGN KEY (selection_id) REFERENCES selections (id)
          ON DELETE CASCADE
          ON UPDATE NO ACTION
        ) WITHOUT ROWID"""
    )
    conn.commit()


def create_selections_indexes(conn: sqlite3.Connection):
    """Creates indexes on the "selections" table

    Args:
        conn (sqlite3.Connection): Sqlite3 connection

    Note:
        * This function should be called after batch insertions.
        * This function ensures the unicity of selections names.
    """
    conn.execute("CREATE UNIQUE INDEX idx_selections ON selections (name)")


def create_selection_has_variant_indexes(conn: sqlite3.Connection):
    """Creates indexes on "selection_has_variant" table

    For joins between selections and variants tables

    Reference:
        * create_selections_indexes()
        * insert_selection()

    Args:
        conn (sqlite3.Connection/sqlite3.Cursor): Sqlite3 connection
    """
    conn.execute(
        "CREATE INDEX idx_selection_has_variant ON selection_has_variant (selection_id)"
    )


def insert_selection(
    conn: Union[sqlite3.Connection, sqlite3.Cursor], query: str, name="no_name", count=0
) -> int:
    """Inserts selection called 'name', with records from SQL query 'query'

    Args:
        conn (Union[sqlite3.Connection, sqlite3.Cursor]): Either a Sqlite3 connection or a cursor. Connects to the current cutevariant project's database.
        query (str): The SQL query that populated the selection 'name'
        name (str, optional): The name of the selection that was created from the query 'query'. Defaults to "no_name".
        count (int, optional): Number of rows in the selection. Defaults to 0.

    Returns:
        Total number of rows in the 'selections' table
    """
    cursor = conn.cursor() if isinstance(conn, sqlite3.Connection) else conn

    cursor.execute(
        "INSERT INTO selections (name, count, query) VALUES (?,?,?)",
        (name, count, query),
    )
    if isinstance(conn, sqlite3.Connection):
        # Commit only if connection is given. => avoid not consistent DB
        conn.commit()
    return cursor.lastrowid


# Delete selections by name
delete_selection_by_name = partial(delete_by_name, table_name="selections")


def create_selection_from_sql(
    conn: sqlite3.Connection,
    query: str,
    name: str,
    count: int = None,
    from_selection=False,
) -> Union[int, None]:
    """Creates a selection record from sql variant query

    Args:
        conn (sqlite3.connection): Sqlite3 connection
        query (str): SQL query that select all variant ids. See `from_selection`
        name (str): Name of selection
        count (int, optional): Variant count
        from_selection (bool, optional): Use a different
            field name for variants ids; `variant_id` if `from_selection` is `True`,
            just `id` if `False`.

    Returns:
        selection_id, if lines have been inserted; None otherwise (rollback).
    """
    cursor = conn.cursor()

    # Compute query count
    # TODO : this can take a while .... need to compute only one from elsewhere
    if count is None:
        count = count_query(cursor, query)

    # Create selection
    selection_id = insert_selection(cursor, query, name=name, count=count)

    # DROP indexes
    # For joins between selections and variants tables
    try:
        cursor.execute("""DROP INDEX idx_selection_has_variant""")
    except sqlite3.OperationalError:
        pass

    # Insert into selection_has_variant table
    # PS: We use DISTINCT keyword to statisfy the unicity constraint on
    # (variant_id, selection_id) of "selection_has_variant" table.
    # TODO: is DISTINCT useful here? How a variant could be associated several
    # times with an association?
    if from_selection:
        # Optimized only for the creation of a selection from set operations
        # variant_id is the only useful column here
        q = f"""
        INSERT INTO selection_has_variant
        SELECT DISTINCT variant_id, {selection_id} FROM ({query})
        """
    else:
        # Fallback
        # Used when creating a selection from a VQL query in the UI
        # Default behavior => a variant is based on chr,pos,ref,alt
        q = f"""
        INSERT INTO selection_has_variant
        SELECT DISTINCT id, {selection_id} FROM ({query})
        """

    cursor.execute(q)
    affected_rows = cursor.rowcount

    # REBUILD INDEXES
    # For joints between selections and variants tables
    create_selection_has_variant_indexes(cursor)

    if affected_rows:
        conn.commit()
        return selection_id
    # Must alert a user because no selection is created here
    conn.rollback()
    return None


def create_selection_from_bed(
    conn: sqlite3.Connection, source: str, target: str, bed_intervals: Iterable[dict]
) -> Union[int, None]:
    """Creates a new selection based on the given intervals taken from a BED file

    Variants whose positions are contained in the intervals specified by the
    BED file will be referenced into the table selection_has_variant under
    a new selection.

    Args:
        conn (sqlite3.connection): Sqlite3 connection
        source (str): Selection name (source); Ex: "variants" (default)
        target (str): Selection name (target)
        bed_intervals (Iterable[dict]): List of intervals
            Each interval is a dict with the expected keys: (chrom, start, end, name)

    Returns:
        lastrowid, if lines have been inserted; None otherwise.
    """

    cur = conn.cursor()

    # Create temporary table
    cur.execute("DROP TABLE IF exists bed_table")
    cur.execute(
        """CREATE TABLE bed_table (
        id INTEGER PRIMARY KEY ASC,
        bin INTEGER DEFAULT 0,
        chr TEXT,
        start INTEGER,
        end INTEGER,
        name INTEGER)"""
    )

    cur.executemany(
        "INSERT INTO bed_table (chr, start, end, name) VALUES (:chrom,:start,:end,:name)",
        bed_intervals,
    )

    if source == "variants":
        source_query = "SELECT variants.id AS variant_id FROM variants"
    else:
        source_query = f"""
        SELECT variants.id AS variant_id FROM variants
        INNER JOIN selections ON selections.name = '{source}'
        INNER JOIN selection_has_variant AS sv ON sv.selection_id = selections.id AND sv.variant_id = variants.id
        """

    query = (
        source_query
        + """
        INNER JOIN bed_table ON
        variants.chr = bed_table.chr AND
        variants.pos >= bed_table.start AND
        variants.pos <= bed_table.end"""
    )

    return create_selection_from_sql(conn, query, target, from_selection=True)


def get_selections(conn: sqlite3.Connection) -> Tuple[dict]:
    """Get selections from the "selections" table

    Args:
        conn (sqlite3.Connection): Sqlite3 connection

    Example:
        >>> get_selections(conn)
        >>> ({"id": ..., "name": ..., "count": ..., "query": ...},
             {"id": ..., "name": ..., "count": ..., "query": ...},
             {"id": ..., "name": ..., "count": ..., "query": ...},
             ...
             {"id": ..., "name": ..., "count": ..., "query": ...})

    Returns:
        Tuple of dictionnaries describing each selection (id, name, count and query)
    """
    conn.row_factory = sqlite3.Row
    return (dict(data) for data in conn.execute("SELECT * FROM selections"))


def delete_selection(conn: sqlite3.Connection, selection_id: int) -> int:
    """Deletes the selection with the given id in the "selections" table

    Args:
        conn (sqlite3.Connection): Sqlite3 connection
        selection_id (int): id (from the 'selections' table) of the selection to remove

    Returns:
        Number of rows deleted
    """

    # Ignore if it is the first selection name aka 'variants'
    if selection_id <= 1:
        return None

    cursor = conn.cursor()

    cursor.execute("DELETE FROM selections WHERE rowid = ?", (selection_id,))
    conn.commit()
    return cursor.rowcount


def edit_selection(conn: sqlite3.Connection, selection: dict) -> int:
    """Updates the name and count of a selection with the given id

    Args:
        conn (sqlite3.Connection): Sqlite3 connection
        selection (dict): Selection dict with keys ('id','count','name')

    Returns:
        Number of rows in the 'selections' table
    """
    cursor = conn.cursor()
    conn.execute(
        "UPDATE selections SET name=:name, count=:count WHERE id = :id", selection
    )
    conn.commit()
    return cursor.rowcount


## wordsets table ===============================================================


def create_table_wordsets(conn: sqlite3.Connection):
    """Creates the table "sets"

    This table stores variants selection saved by the user:
        - name: name of the set of variants
        - value: number of variants concerned by this set

    TODO: Denormalization of this table **WILL** BE a problem in the future...
        But i'm fed up of these practices.

    TODO: for now the one to many relation is not implemented

    Args:
        conn (sqlite3.Connection): Sqlite3 connection
    """
    cursor = conn.cursor()
    cursor.execute(
        """CREATE TABLE wordsets (
        id INTEGER PRIMARY KEY ASC,
        name TEXT,
        value TEXT,
        UNIQUE (name, value)
        )"""
    )

    conn.commit()


def sanitize_words(words: Iterable[str]) -> Set[str]:
    """Returns a set of cleaned words from the given iterable

    Args:
        words (Iterable[str]): A collection of strings (either a file handle or generic iterable collection)

    Returns:
        A set of strings taken from the 'words' collection, having removed entries with whitespaces.

    !!! note "See also"

        [`cutevariant.core.sql.import_wordset_from_file`][cutevariant.core.sql.import_wordset_from_file]

    !!! todo "To do"
        Generate doc for wordset_plugin to link to `cutevariant.gui.plugins.word_set.widgets.WordListDialog.load_file`
    """
    # Search whitespaces
    expr = re.compile("[ \t\n\r\f\v]")
    data = set()

    for line in words:
        striped_line = line.strip()

        if not striped_line or expr.findall(striped_line):
            # Skip lines with whitespaces
            continue
        data.add(striped_line)
    return data


def import_wordset_from_file(
    conn: sqlite3.Connection, wordset_name: str, filename: str
) -> int:
    r"""Create Word set from the given file

    Args:
        conn (sqlite3.Connection): Sqlite3 connection
        wordset_name (str): Name of the Word set
        filename (str): File to be imported, expects 1 word per line.

    Returns:
        Number of rows affected during insertion (number of words inserted).
        None if 0 word can be inserted.

    Current data filtering (same as in the word_set plugin):
        - Strip trailing spaces and EOL characters
        - Skip empty lines
        - Skip lines with whitespaces characters (``[ \t\n\r\f\v]``)

    !!! example
        - The following line will be skipped:
          ``"abc  def\tghi\t  \r\n"``
        - The following line will be cleaned:
          ``"abc\r\n"``
    """
    # Search whitespaces
    with open(filename, "r") as f_h:
        data = sanitize_words(f_h)

    if not data:
        return

    # Insertion
    cursor = conn.cursor()
    cursor.executemany(
        "INSERT INTO wordsets (name, value) VALUES (?,?)",
        it.zip_longest(tuple(), data, fillvalue=wordset_name),
    )
    conn.commit()
    return cursor.rowcount


def import_wordset_from_list(conn: sqlite3.Connection, wordset_name, words: list):
    r"""Create Word set from the given list

    Args:
        wordset_name: Name of the Word set
        words: A list of words

    Returns:
        Number of rows affected during insertion (number of words inserted).
        None if 0 word can be inserted.

    Current data filtering (same as in the word_set plugin):
        - Strip trailing spaces and EOL characters
        - Skip empty lines
        - Skip lines with whitespaces characters (``[ \t\n\r\f\v]``)

    Examples:
        - The following line will be skipped:
          ``"abc  def\tghi\t  \r\n"``
        - The following line will be cleaned:
          ``"abc\r\n"``
    """
    # Search whitespaces

    data = sanitize_words(words)

    if not data:
        return

    # Insertion
    cursor = conn.cursor()
    cursor.executemany(
        "INSERT INTO wordsets (name, value) VALUES (?,?)",
        it.zip_longest(tuple(), data, fillvalue=wordset_name),
    )
    conn.commit()
    return cursor.rowcount


# Delete set by name
delete_set_by_name = partial(delete_by_name, table_name="wordsets")


def get_wordsets(conn: sqlite3.Connection) -> Generator[dict, None, None]:
    """Yields dicts of (wordset_name,word_count)

    Args:
        conn (sqlite3.Connection): Sqlite3 connection

    Yields:
        Generator[dict,None,None]: dicts containing keys wordset_name and word_count

    !!! example
        ```python
        >>> conn = get_sql_connection("test.db")
        >>> get_wordsets(conn)
        >>> {
            "Krebs cycles genes" : 10,
            "Genes of concern" : 20
        }
        ```

    """
    for row in conn.execute(
        "SELECT name, COUNT(*) as 'count' FROM wordsets GROUP BY name"
    ):
        yield dict(row)


def get_words_in_set(
    conn: sqlite3.Connection, wordset_name: str
) -> Generator[str, None, None]:
    """Yields every string in the wordset 'wordset_name'

    Args:
        conn (sqlite3.Connection): Sqlite3 connection
        wordset_name (str): Name of the wordset to retrieve content from

    Yields:
        Generator[dict,None,None]: One string from the wordset 'wordset_name'
    """
    for row in conn.execute(
        "SELECT DISTINCT value FROM wordsets WHERE name = ?", (wordset_name,)
    ):
        yield dict(row)["value"]


def intersect_wordset(conn, name: str, wordsets: list):
    """Create new `name` wordset from intersection of `wordsets`

    Args:
        conn (sqlite.Connection):
        name (str): A wordset Name
        wordsets (list): List of wordset name

    """
    query = f"""INSERT INTO wordsets (name, value) 
            SELECT '{name}' as name,  value FROM """

    query += (
        "("
        + " INTERSECT ".join(
            [f"SELECT value FROM wordsets WHERE name = '{w}'" for w in wordsets]
        )
        + ")"
    )

    print(query)
    conn.execute(query)
    conn.commit()


def union_wordset(conn, name: str, wordsets=[]):
    """Create new `name` wordset from union of `wordsets`

    Args:
        conn (sqlite.Connection):
        name (str): A wordset Name
        wordsets (list): List of wordset name

    """
    query = f"""INSERT INTO wordsets (name, value) 
            SELECT '{name}' as name,  value FROM """

    query += (
        "("
        + " UNION ".join(
            [f"SELECT value FROM wordsets WHERE name = '{w}'" for w in wordsets]
        )
        + ")"
    )

    conn.execute(query)
    conn.commit()


def subtract_wordset(conn, name: str, wordsets=[]):
    """Create new `name` wordset from subtract of `wordsets`

    Args:
        conn (sqlite.Connection):
        name (str): A wordset Name
        wordsets (list): List of wordset name

    """
    query = f"""INSERT INTO wordsets (name, value) 
            SELECT '{name}' as name,  value FROM """

    query += (
        "("
        + " EXCEPT ".join(
            [f"SELECT value FROM wordsets WHERE name = '{w}'" for w in wordsets]
        )
        + ")"
    )

    conn.execute(query)
    conn.commit()


## Operations on sets of variants ==============================================


def get_query_columns(mode: str = "variant"):
    """(DEPRECATED FOR NOW, NOT USED)

    Handy func to get columns to be queried according to the group by argument

    .. note:: Used by intersect_variants, union_variants, subtract_variants
        in order to avoid code duplication.
    """
    if mode == "site":
        return "chr,pos"

    if mode == "variant":
        # Not used
        return "variant_id"

    raise NotImplementedError


def intersect_variants(query1: str, query2: str, **kwargs) -> str:
    """Builds a SQL query to get variants from both query1 AND query2

    Args:
        query1 (str): LHS operand of the intersection query (SQL)
        query2 (str): RHS operand of the intersection query (SQL)

    Returns:
        Resulting query (SQL)

    !!! info "Nota Bene"

        Try to handle precedence of operators.
        - The precedence of UNION and EXCEPT are similar, they are processed from
        left to right.
        - Both of the operations are fulfilled before INTERSECT operation,
        i.e. they have precedence over it.

    """
    return f"""SELECT * FROM ({query1} INTERSECT {query2})"""


def union_variants(query1, query2, **kwargs) -> str:
    """Builds a SQL query to get variants from either query1 OR query2 (or both)

    Args:
        query1 (str): LHS operand of the union query (SQL)
        query2 (str): RHS operand of the union query (SQL)

    Returns:
        Resulting query (SQL)

    !!! info "Nota Bene"

        Try to handle precedence of operators.
        - The precedence of UNION and EXCEPT are similar, they are processed from
        left to right.
        - Both of the operations are fulfilled before INTERSECT operation,
        i.e. they have precedence over it.

    """
    return f"""{query1} UNION {query2}"""


def subtract_variants(query1, query2, **kwargs) -> str:
    """Builds a SQL query to get variants that are in query1 BUT NOT in query2

    Args:
        query1 (str): LHS operand of the difference query (SQL)
        query2 (str): RHS operand of the difference query (SQL)

    Returns:
        Resulting query (SQL)

    !!! info "Nota Bene"

        Try to handle precedence of operators.
        - The precedence of UNION and EXCEPT are similar, they are processed from
        left to right.
        - Both of the operations are fulfilled before INTERSECT operation,
        i.e. they have precedence over it.

    """
    return f"""{query1} EXCEPT {query2}"""


## fields table ================================================================


def create_table_fields(conn: sqlite3.Connection):
    """Creates the table "fields"

    This table contain fields. A field is a column with its description and type;
    it can be choose by a user to build a Query
    Fields are the columns of the tables: variants, annotations and sample_has_variant.
    Fields are extracted from reader objects and are dynamically constructed.

    variants:
    chr,pos,ref,alt,filter,qual,dp,af,etc.

    annotations:
    gene,transcript,etc.

    sample_has_variant:
    genotype

    Args:
        conn (sqlite3.Connection): Sqlite3 connection
    """
    cursor = conn.cursor()
    cursor.execute(
        """CREATE TABLE fields
        (id INTEGER PRIMARY KEY, name TEXT, category TEXT, type TEXT, description TEXT)
        """
    )
    conn.commit()


def insert_field(
    conn: sqlite3.Connection,
    name: str = "no_name",
    category: str = "variants",
    type: str = "text",
    description: str = str(),
) -> int:
    """
    Inserts one field record (NOT USED)

    Args:
        conn (sqlite3.Connection): Sqlite3 connection
        name (str): Name of the field to insert
        category (str): Category field name.
            !!! warning
                The default is "variants". Don't use sample as category name
        type (str): sqlite type which can be: INTEGER, REAL, TEXT
            !!! todo "To do"
                Check this argument...
        description (str): Text that describes the field (showed to the user).
    Returns:
        Last row id
    """
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO fields VALUES (?, ?, ?, ?)", (name, category, type, description)
    )
    conn.commit()
    return cursor.lastrowid


def insert_many_fields(conn: sqlite3.Connection, data: List[dict]):
    """Inserts multiple fields into "fields" table using one commit

    !!! example
        ```python
        >>> insert_many_fields(conn, [{"name":"sacha", "category":"variant", "type" : "TEXT", "description"="a description"}])
        >>> insert_many_fields(conn, reader.get_fields())
        ```

    !!! seealso "See also"
        - [`cutevariant.core.sql.insert_field`][cutevariant.core.sql.insert_field]
        - `abstractreader`

    Args:
        conn (sqlite3.Connection): Sqlite3 connection
        data (List[dict]): List of dicts describing the fields to insert (each dict should contain 'name','category', 'type' and 'description' keys)
    """
    cursor = conn.cursor()
    cursor.executemany(
        """
        INSERT INTO fields (name,category,type,description)
        VALUES (:name,:category,:type,:description)
        """,
        data,
    )
    conn.commit()


@lru_cache()
def get_fields(conn: sqlite3.Connection) -> Tuple[dict]:
    """Returns fields from table 'fields' as tuple of dictionnary

    !!! seealso "See also"
        insert_many_fields

    conn (Sqlite3.Connection): Sqlite3 connection

    Returns:
        Tuple of dictionnaries, each one describing one field in the table 'fields' (keys are 'name','category', 'type' and 'description')
    """
    conn.row_factory = sqlite3.Row
    return tuple(dict(data) for data in conn.execute("SELECT * FROM fields"))


@lru_cache()
def get_field_by_category(conn: sqlite3.Connection, category: str) -> Tuple[dict]:
    """Returns all fields from within the given category

    Args:
        conn (sqlite3.Connection): Sqlite3 connection
        category (str): Name of the category to retrieve the fields info from

    Returns:
        Tuple of dictionnaries, each one describing one field in the table 'fields', where category == category

    !!! seealso "See also"
        get_fields
    """
    return tuple(field for field in get_fields(conn) if field["category"] == category)


def get_field_by_name(conn: sqlite3.Connection, field_name: str) -> Union[dict, None]:
    """Returns 'name','category', 'type' and 'description' about field where name == 'field_name'

    Args:
        conn (sqlite3.Connection): Sqlite3 connection
        field_name (str): Name of the field to query information about

    Returns:
        dict with keys 'name','category', 'type' and 'description'.
        None if there is no field with name field_name in the 'field' table

    !!! warning
        If two fields from different categories have the same name, the behavior is UNDEFINED !
        In these cases, we recommend using get_field_by_category or get_fields

    """
    conn.row_factory = sqlite3.Row
    field_data = conn.execute(
        "SELECT * FROM fields WHERE name = ? ", (field_name,)
    ).fetchone()
    return dict(field_data) if field_data else None


def get_field_range(
    conn: sqlite3.Connection, field_name: str, sample_name: str = None
) -> Union[Tuple, None]:
    """Return (min,max) of field_name in records

    Args:
        conn (Sqlite3.Connection): Sqlite3 connection
        field_name (str): field name to get the range of
        sample_name (str): sample name. Mandatory for fields in the "samples" category

    Returns:
        (min, max) of field_name
        None if the field can't be processed with mix/max functions (or doesn't exist)
    """
    field = get_field_by_name(conn, field_name)
    if not field:
        return None

    table = field["category"]  # variants, or annotations or samples
    if table == "samples":
        if not sample_name:
            raise ValueError("Pass sample parameter for sample fields")
        query = f"""SELECT min({field_name}), max({field_name})
        FROM sample_has_variant
        JOIN samples ON sample_has_variant.sample_id = samples.id
        WHERE samples.name='{sample_name}'
        """
    else:
        query = f"SELECT min({field_name}), max({field_name}) FROM {table}"

    result = tuple(conn.execute(query).fetchone())
    if result in ((None, None), ("", "")):
        return None

    return result


def get_field_unique_values(conn, field_name: str, like: str = None, limit=None):
    """Return unique record values for a field name

    Returns:
        List of unique values stored in the column field_name in the database.
    """

    if field_name.startswith("ann."):
        field_name = field_name.replace("ann.", "")

    if field_name.startswith("samples."):
        #  TODO replace samples ...
        _, *_, field = field_name.split(".")
        field_name = field

    field = get_field_by_name(conn, field_name)
    if not field:
        return []
    table = field["category"]  # variants, or annotations or samples

    if table == "samples":
        query = f""" SELECT DISTINCT `{field_name}` FROM sample_has_variant """

    elif table == "annotations":
        query = f""" SELECT DISTINCT `{field_name}` FROM annotations """

    else:
        query = f"SELECT DISTINCT `{field_name}` FROM {table}"

    if like:
        query += f" WHERE `{field_name}` LIKE '{like}'"

    if limit:
        query += " LIMIT " + str(limit)

    return [i[field_name] for i in conn.execute(query)]


## annotations table ===========================================================


def create_table_annotations(conn: sqlite3.Connection, fields: Iterable[dict]):
    """Creates "annotations" table which contains dynamics fields

    Args:
        fields (Iterable): Iterable of SQL fields. Each field is a dict with "name" and "type" keys. "type" value **must** be a valid SQL type (i.e. one of "TEXT","NUMERIC","INTEGER","REAL", or "BLOB")

    !!! example
        ```python
        >>> import sql
        >>> conn = sql.get_sql_connection("test.db")
        >>> sql.create_table_annotations(conn,[{"name":"chr","type":"TEXT"},{"name":"pos","type":"INT"}])
        ```
    """
    schema = ",".join([f'`{field["name"]}` {field["type"]}' for field in fields])

    if not schema:
        # Create minimum annotation table... Can be use later for dynamic annotation.
        # TODO : we may want to fix annotation fields .
        schema = "gene TEXT, transcript TEXT"
        LOGGER.debug(
            "create_table_annotations:: No annotation fields detected! => Fallback"
        )
        # return

    cursor = conn.cursor()
    # TODO: no primary key/unique index for this table?

    cursor.execute(f"CREATE TABLE annotations (variant_id INTEGER NOT NULL, {schema})")

    conn.commit()


def create_annotations_indexes(conn):
    """Creates indexes on the "annotations" table

    Args:
        conn (sqlite3.Connection) : Sqlite3 connection


    !!! warning
        This function must be called after batch insertions.

    !!! example

        ```sql
        SELECT *, group_concat(annotations.rowid) FROM variants
        LEFT JOIN annotations ON variants.rowid = annotations.variant_id
        WHERE pos = 0
        GROUP BY chr,pos
        LIMIT 100
        ```
    """
    # Allow search on variant_id
    conn.execute("CREATE INDEX idx_annotations ON annotations (variant_id)")


def get_annotations(
    conn: sqlite3.Connection, variant_id: int
) -> Generator[dict, None, None]:
    """Get variant annotations for the variant with the given id. Yields one dict of annotations for each annotation this variant has

    Args:
        conn (sqlite3.Connection): Sqlite3 connection
        variant_id (int): ID of the variant to get annotions for

    Yields:
        dict: Annotation data for this variant

    """
    conn.row_factory = sqlite3.Row
    for annotation in conn.execute(
        f"SELECT * FROM annotations WHERE variant_id = {variant_id}"
    ):
        yield dict(annotation)


## variants table ==============================================================


def create_table_variants(conn: sqlite3.Connection, fields: List[dict]):
    """Creates tables "variants" and "sample_has_variant" tables which contains dynamics fields

    Args:
        conn (sqlite3.Connection): Sqlite3 connection
        fields (List[dict]): List of 'fields' (dicts with at least name and type, optionally constraint) to put in tables variants and 'sample_has_variant'

    !!! example
        ```python
        >>> fields = get_fields()
        >>> create_table_variants(conn, fields)
        ```
    !!! seealso "See also"
        get_fields

    !!! note

        "gt" field in "sample_has_variant" = Patient's genotype.
         - Patient without variant: gt = 0: Wild homozygote
         - Patient with variant in the heterozygote state: gt = -1: Heterozygote
         - Patient with variant in the homozygote state: gt = 2: Homozygote

    """
    cursor = conn.cursor()

    # Primary key MUST NOT have NULL fields !
    # PRIMARY KEY should always imply NOT NULL.
    # Unfortunately, due to a bug in some early versions, this is not the case in SQLite.
    # For the purposes of UNIQUE constraints, NULL values are considered distinct
    # from all other values, including other NULLs.
    schema = ",".join(
        [
            f'`{field["name"]}` {field["type"]} {field.get("constraint", "")}'
            for field in fields
            if field["name"]
        ]
    )

    LOGGER.debug("create_table_variants:: schema: %s", schema)
    # Unicity constraint or NOT NULL fields (Cf VcfReader, FakeReader, etc.)
    # NOTE: specify the constraint in CREATE TABLE generates a lighter DB than
    # a separated index... Don't know why.
    cursor.execute(
        f"""CREATE TABLE variants (id INTEGER PRIMARY KEY, {schema},
        UNIQUE (chr,pos,ref,alt))"""
    )
    # cursor.execute(f"""CREATE UNIQUE INDEX idx_variants_unicity ON variants (chr,pos,ref,alt)""")

    conn.commit()


def create_variants_indexes(conn):
    """Create indexes for the "variants" table

    !!! warning
        This function must be called after batch insertions.

    !!! example

        ```sql
        SELECT *, group_concat(annotations.rowid) FROM variants
        LEFT JOIN annotations ON variants.rowid = annotations.variant_id
        WHERE pos = 0
        GROUP BY chr,pos
        LIMIT 100
        ```

    """
    # Complementary index of the primary key (sample_id, variant_id)
    conn.execute(
        "CREATE INDEX idx_sample_has_variant ON sample_has_variant (variant_id)"
    )

    conn.execute("CREATE INDEX idx_variants_pos ON variants (pos)")
    conn.execute("CREATE INDEX idx_variants_ref_alt ON variants (ref, alt)")


def get_one_variant(
    conn: sqlite3.Connection,
    variant_id: int,
    with_annotations=False,
    with_samples=False,
) -> dict:
    r"""Get the variant with the given id



    Args:
        conn (sqlite3.Connection): Sqlite3 connection
        variant_id (int): Database id of the variant
        with_annotations (bool, optional): Add annotations items. Default is True
        with_samples (bool, optional): add samples items. Default is True

    Returns:
        A variant item with all fields in "variants" table. Including:
            - all fields of annotations table if `with_annotations` is True.
            - all fields of sample_has_variant associated to all samples if `with_samples` is True.
            In either case, 'annotations' and 'samples' are returned as lists at their respective keys (empty lists if not requested)

    !!! example
        ```python
        >>> conn = sql.get_sql_connection("test.db")
        >>> variant = sql.get_one_variant(conn,42,with_annotations=True)
        {'id': 42,
            'count_hom': 0,
            'count_het': 1,
            'count_ref': 0,
            'count_var': 1,
            'is_snp': 1,
            'annotation_count': **1**,
            {...}
            'annotations': [
            {
                'variant_id': 42,
                'allele': 'A',
                'consequence': 'intergenic_region',
                {...}
            }],
            'samples': []
        }
        ```

    !!! todo "To do"
        with_annotations, with_samples are quite useless and not used for now
    """
    conn.row_factory = sqlite3.Row
    # Cast sqlite3.Row object to dict because later, we use items() method.
    variant = dict(
        conn.execute(
            f"SELECT * FROM variants WHERE variants.id = {variant_id}"
        ).fetchone()
    )

    variant["annotations"] = []
    if with_annotations:
        variant["annotations"] = [
            dict(annotation)
            for annotation in conn.execute(
                f"SELECT * FROM annotations WHERE variant_id = {variant_id}"
            )
        ]

    variant["samples"] = []
    if with_samples:
        variant["samples"] = [
            dict(sample)
            for sample in conn.execute(
                f"""SELECT samples.name, sample_has_variant.* FROM sample_has_variant
                LEFT JOIN samples on samples.id = sample_has_variant.sample_id
                WHERE variant_id = {variant_id}"""
            )
        ]

    return variant


def update_variant(conn: sqlite3.Connection, variant: dict):
    """Used by widgets to save various modifications in a variant.

    Args:
        conn (sqlite3.Connection): Sqlite3 connection
        variant (dict): key,value pairs of fields to replace where the 'id' key indicates which variant to update

    Raises:
        KeyError: if 'id' key is not in the given variant
    """
    if "id" not in variant:
        raise KeyError("'id' key is not in the given variant <%s>" % variant)

    unzip = lambda l: list(zip(*l))

    # Get fields and values in separated lists
    placeholders, values = unzip(
        [(f"`{key}` = ? ", value) for key, value in variant.items() if key != "id"]
    )
    query = (
        "UPDATE variants SET " + ",".join(placeholders) + f" WHERE id = {variant['id']}"
    )
    # LOGGER.info(
    #     "Update variant %s: placeholders: %s; values %s",
    #     variant["id"], placeholders, values
    # )
    cursor = conn.cursor()
    cursor.execute(query, values)
    conn.commit()


def get_variants_count(conn: sqlite3.Connection):
    """Get the number of variants in the "variants" table
    Args:
        conn (sqlite3.Connection): Sqlite3 connection
    """
    return count_query(conn, "variants")


def get_variants(
    conn: sqlite3.Connection,
    fields: List[str],
    source: str = "variants",
    filters: dict = {},
    order_by: str = None,
    order_desc: bool = True,
    limit: int = 50,
    offset: int = 0,
    group_by={},
    having={},  # {"op":">", "value": 3  }
    **kwargs,
) -> Generator[dict, None, None]:
    """Yields a dict for each variant passing filters. Each dict contains keys for every field in fields, where fields starting with 'ann.' or 'sample.'
    are in lists under 'annotations' and 'samples' keys respectively.

    Args:
        conn (sqlite3.Connection): Sqlite3 connection
        fields (List[str]): List of fields you want to retrieve. Fields in annotations table must be prefixed with ann, whereas fields in the sample_has_variant table should be prefixed with 'sample.{sample_name}.'
        source (str, optional): Selection you want to retrieve the variants from. Defaults to "variants".
        filters (dict, optional): Tree of conditions, linked by logical operators (either $and or $or). Defaults to {}.
        order_by (str, optional): Name of the field to order the result by. Defaults to None.
        order_desc (bool, optional): Whether to order in descendent order or not. Defaults to True.
        limit (int, optional): Defines a limit for the request. Helps keeping memory safe. Defaults to 50.
        offset (int, optional): Offset of the SQL request. Use it if you need the next N+p pages after having requested the first N. Defaults to 0.
        group_by (dict, optional): Deprecated. Defaults to {}.
        having (dict, optional): Deprecated. Defaults to {}.

    Yields:
        Generator[dict, None, None]: A dict containing all the requested fields about a variant that matches the query. Each variant unique ID will be yielded
        only once, no matter how many annotations refer to it

    !!! seealso "See also"
        get_one_variant

    """
    # TODO : rename as get_variant_as_tables ?
    query = build_sql_query(
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

    for i in conn.execute(query):
        # THIS IS INSANE... SQLITE DOESNT RETURN ALIAS NAME WITH SQUARE BRACKET....
        # I HAVE TO replace [] by () and go back after...
        # TODO : Change VQL Syntax from [] to () would be a good alternative
        # @See QUERYBUILDER
        # See : https://stackoverflow.com/questions/41538952/issue-cursor-description-never-returns-square-bracket-in-column-name-python-2-7-sqlite3-alias
        yield {k.replace("(", "[").replace(")", "]"): v for k, v in dict(i).items()}


# def get_variants_tree(
#     conn: sqlite3.Connection,
#     **kwargs,
# ):
# pass
# for variant in get_variants(conn, **kwargs):

#     item = {}
#     annotations = []
#     samples = {}

#     for key, value in variant.items():
#         if key.startswith("ann."):
#             value = str(value)
#             annotations.append(value[4:])

#         elif key.startswith("sample."):
#             _, *sample, field = key.split(".")
#             sample = ".".join(sample)

#             if "sample" not in samples:
#                 samples[sample] = list()
#             samples[sample].append()

#         else:
#             item[key] = value

#     if annotations:
#         item["annotations"] = annotations

#     if samples:
#         item["samples"] = samples

#     yield item


def async_insert_many_variants(
    conn: sqlite3.Connection, data: list, total_variant_count=None, yield_every=3000
) -> Generator[Tuple[int, str], None, None]:
    """Insert many variants from data into variants table

    Args:
        conn (sqlite3.Connection): Sqlite connection
        data (list): list of variant dictionnary which contains same number of key than fields numbers.
        total_variant_count (None, optional): total variant count, to compute progression
        yield_every (int, optional): yield a progress mesasge every {yield_every} insertion

    Yields:
        (int,str): Yield a tuple with progression and message. Progression is 0 if total_variant_count is not set.

    !!! example
        Insert many variant:
        ```python
        >>> conn = get_sql_connection("example.db")
        >>> insert_many_variant(conn, [{chr:"chr1", pos:24234, alt:"A","ref":T }])
        >>> insert_many_variant(conn, reader.get_variants())
        ```

    !!! todo "To do"
        with large dataset, need to cache import
        handle insertion errors...

    !!! note
        About using INSERT OR IGNORE: They avoid the following errors:
        Using reader, this can take a while
        Upon insertion of a duplicate key where the column must contain
        a PRIMARY KEY or UNIQUE constraint Upon insertion of NULL value where the column
        has a NOT NULL constraint.
    """

    def build_columns_and_placeholders(table_name):
        """Build a tuple of columns and "?" placeholders for INSERT queries"""
        # Get columns description from the given table
        cols = get_table_columns(conn, table_name)
        # Build dynamic insert query
        # INSERT INTO variant qcol1, qcol2.... VALUES ?, ?
        tb_cols = ",".join([f"`{col}`" for col in cols])
        tb_places = ",".join(["?" for place in cols])
        return tb_cols, tb_places

    # TODO: Can we avoid this step ? This function should receive columns names
    # because all the tables were created before...
    # Build placeholders
    var_cols, var_places = build_columns_and_placeholders("variants")
    ann_cols, ann_places = build_columns_and_placeholders("annotations")

    var_columns = get_table_columns(conn, "variants")
    ann_columns = get_table_columns(conn, "annotations")
    sample_columns = get_table_columns(conn, "sample_has_variant")

    # Get samples with samples names as keys and sqlite rowid as values
    # => used as a mapping for samples ids
    samples_id_mapping = dict(conn.execute("SELECT name, id FROM samples"))

    # Check SQLite version and build insertion queries for variants
    # Old version doesn't support ON CONFLICT ..target.. DO ... statements
    # to handle violation of unicity constraint.
    old_sqlite_version = parse_version(sqlite3.sqlite_version) < parse_version("3.24.0")

    if old_sqlite_version:
        LOGGER.warning(
            "async_insert_many_variants:: Old SQLite version: %s"
            " - Fallback to ignore errors!",
            sqlite3.sqlite_version,
        )
        # /!\ This syntax is SQLite specific
        # /!\ We mask all errors here !
        variant_insert_query = f"""INSERT OR IGNORE INTO variants ({var_cols})
                VALUES ({var_places})"""

    else:
        # Handle conflicts on the primary key
        variant_insert_query = f"""INSERT INTO variants ({var_cols})
                VALUES ({var_places})
                ON CONFLICT (chr,pos,ref,alt) DO NOTHING"""

    # Insertion - Begin transaction
    cursor = conn.cursor()

    # Loop over variants
    errors = 0
    progress = 0
    variant_count = 0
    for variant_count, variant in enumerate(data, 1):

        # Insert current variant
        # Use default dict to handle missing values
        # LOGGER.debug(
        #    "async_insert_many_variants:: QUERY: %s\nVALUES: %s",
        #    variant_insert_query,
        #    variant,
        # )

        # Create list of value to insert
        # ["chr",234234,"A","G"]
        # if field key is missing, set a default value to None !
        default_values = defaultdict(lambda: None, variant)
        values = [default_values[col] for col in var_columns]

        cursor.execute(variant_insert_query, values)

        # If the row is not inserted we skip this erroneous variant
        # and the data that goes with
        if cursor.rowcount == 0:
            LOGGER.error(
                "async_insert_many_variants:: The following variant "
                "contains erroneous data; most of the time it is a "
                "duplication of the primary key: (chr,pos,ref,alt). "
                "Please check your data; this variant and its attached "
                "data will not be inserted!\n%s",
                variant,
            )
            errors += 1
            continue

        # Get variant rowid
        variant_id = cursor.lastrowid

        # If variant has annotation data, insert record into "annotations" table
        # One-to-many relationships
        if "annotations" in variant:
            # print("VAR annotations:", variant["annotations"])

            # [{'allele': 'T', 'consequence': 'intergenic_region', 'impact': 'MODIFIER', ...}]
            # The aim is to execute all insertions through executemany()
            # We remove the placeholder :variant_id from places,
            # and fix it's value.
            # TODO: handle missing values;
            # Les dict de variant["annotations"] contiennent a priori déjà
            # tous les champs requis (mais vides) car certaines annotations
            # ont des données manquantes.
            # A t'on l'assurance de cela ?
            # Dans ce cas pourquoi doit-on bricoler le variant lui-meme avec un
            # defaultdict(str,variant)) ? Les variants n'ont pas leurs champs par def ?

            values = []
            for ann in variant["annotations"]:
                default_values = defaultdict(lambda: None, ann)
                value = [default_values[col] for col in ann_columns[1:]]
                value.insert(0, variant_id)
                values.append(value)

            temp_ann_places = ",".join(["?"] * (len(ann_columns)))

            q = f"""INSERT INTO annotations ({ann_cols})
                VALUES ({temp_ann_places})"""

            cursor.executemany(q, values)

        # If variant has sample data, insert record into "sample_has_variant" table
        # Many-to-many relationships
        if "samples" in variant:
            # print("VAR samples:", variant["samples"])
            # [{'name': 'NORMAL', 'gt': 1, 'AD': '64,0', 'AF': 0.0, ...}]
            # Insertion only if the current sample name is in samples_names
            # (authorized sample names already in the database)
            #
            # Is this test usefull since samples that are in the database
            # have been inserted from the same source file (or it is not the case ?) ?
            # => yes, we can use external ped file
            # Retrieve the id of the sample to build the association in
            # "sample_has_variant" table carrying the data "gt" (genotype)

            samples = []
            for sample in variant["samples"]:
                sample_id = samples_id_mapping[sample["name"]]
                default_values = defaultdict(lambda: None, sample)
                sample_value = [sample_id, variant_id]
                sample_value += [default_values[i] for i in sample_columns[2:]]
                samples.append(sample_value)

            placeholders = ",".join(["?"] * len(sample_columns))

            q = f"INSERT INTO sample_has_variant VALUES ({placeholders})"
            cursor.executemany(q, samples)

        # Yield progression
        if variant_count % yield_every == 0:
            if total_variant_count:
                progress = variant_count / total_variant_count * 100

            yield progress, f"{variant_count} variants inserted."

    # Commit the transaction
    conn.commit()

    yield 97, f"{variant_count - errors} variant(s) has been inserted."

    # Create default selection (we need the number of variants for this)
    insert_selection(
        conn, "", name=cm.DEFAULT_SELECTION_NAME, count=variant_count - errors
    )


def insert_many_variants(conn, data, **kwargs):
    """Wrapper for debugging purpose"""
    for _, _ in async_insert_many_variants(conn, data, kwargs):
        pass


def get_variant_as_group(
    conn,
    groupby: str,
    fields: list,
    source: str,
    filters: dict,
    order_by="count",
    limit=50,
):

    subquery = build_sql_query(
        conn, fields=fields, source=source, filters=filters, limit=None
    )

    query = f"""SELECT `{groupby}`, COUNT(`{groupby}`) AS count 
    FROM ({subquery}) GROUP BY `{groupby}` ORDER BY count LIMIT {limit}"""
    for i in conn.execute(query):
        yield dict(i)


## samples table ===============================================================


def create_table_samples(conn: sqlite3.Connection, fields: List[dict] = []):
    """Create samples table with the given fields
    Args:
        conn (sqlite3.Connection): Sqlite3 connection
        fields (List[dict]): List of fields in the samples table. Each field must have at least 'name' and 'type' keys, and optionally a 'constraint' field
    """
    cursor = conn.cursor()
    # sample_id is an alias on internal autoincremented 'rowid'
    cursor.execute(
        """CREATE TABLE samples (
        id INTEGER PRIMARY KEY ASC,
        name TEXT,
        family_id TEXT DEFAULT 'fam',
        father_id INTEGER DEFAULT 0,
        mother_id INTEGER DEFAULT 0,
        sex INTEGER DEFAULT 0,
        phenotype INTEGER DEFAULT 0
        )"""
    )
    conn.commit()

    fields = list(fields)

    schema = ",".join(
        [
            f'`{field["name"]}` {field["type"]} {field.get("constraint", "")}'
            for field in fields
            if field["name"]
        ]
    )

    if not fields:
        schema = "gt INTEGER DEFAULT -1"

    cursor.execute(
        f"""CREATE TABLE sample_has_variant  (
        sample_id INTEGER NOT NULL,
        variant_id INTEGER NOT NULL,
        {schema},
        PRIMARY KEY (sample_id, variant_id),
        FOREIGN KEY (sample_id) REFERENCES samples (id)
          ON DELETE CASCADE
          ON UPDATE NO ACTION
        ) WITHOUT ROWID
       """
    )

    conn.commit()


def insert_sample(conn: sqlite3.Connection, name: str = "no_name"):
    """Insert one sample in samples table (USED in TESTS)

    Args:
        conn (sqlite3.Connection): Sqlite3 connection
        name (str): Name of the sample to insert
    Returns
        int: Last row id
    """
    cursor = conn.cursor()
    cursor.execute("INSERT INTO samples (name) VALUES (?)", [name])
    conn.commit()
    return cursor.lastrowid


def insert_many_samples(conn: sqlite3.Connection, samples: List[str]):
    """Insert many samples at a time in the 'samples' table

    Args:
        conn (sqlite3.Connection): Sqlite3 connection
        samples (List[str]): List of samples names

    !!! todo "To do"
        only names in this list ?
    """
    cursor = conn.cursor()
    cursor.executemany(
        "INSERT INTO samples (name) VALUES (?)", ((sample,) for sample in samples)
    )
    conn.commit()


def get_samples(conn: sqlite3.Connection) -> Generator[dict, None, None]:
    """Get samples from sample table


    Args:
        conn (sqlite3.Connection): Sqlite3 connection

    Yields:
        Each yielded dictionnary contains keys and values to identify the sample by its id, name, family_id and so on.

    Returns:
        Generator of dictionnaries

    !!! example
        ```python
        >>> conn = sql.get_sql_connection("test.db")
        >>> list(get_samples(conn))
        >>> [
                {
                    'id': 1,
                    'name': 'bobby',
                    'family_id': 'fam',
                    'father_id': 0,
                    'mother_id': 0,
                    'sex': 0,
                    'phenotype': 0
                },
                {
                    ...
                },
                ...
        ]
        ```
    !!! seealso "See also"
        update_sample
    """
    conn.row_factory = sqlite3.Row
    return (dict(data) for data in conn.execute("SELECT * FROM samples"))


def get_sample_annotations(
    conn: sqlite3.Connection, variant_id: int, sample_id: int
) -> dict:
    """Get sample annotations for given sample id and variant id

    Args:
        conn (sqlite3.Connection): Sqlite3 connection
        variant_id (int): Variant ID you want the sample annotations from
        sample_id (int): The sample ID you want the variant annotation for

    Returns:
        A dict with keys 'sample_id', 'variant_id' (the same as the arguments) and as many key value pairs as there are annotations fields for this sample

    """
    conn.row_factory = sqlite3.Row
    return dict(
        conn.execute(
            f"SELECT * FROM sample_has_variant WHERE variant_id = {variant_id} and sample_id = {sample_id}"
        ).fetchone()
    )


def get_sample_annotations_by_variant(
    conn: sqlite3.Connection, variant_id: int
) -> List[dict]:
    """Get all samples annotations for variant with variant_id

    Args:
        conn (sqlite3.Connection): Sqlite3 connection
        variant_id (int): The variant you want to know the sample annotations for

    Returns:
        List of sample annotations. Each dict has a variant_id key (the same as in the args), the sample_id you are getting the annotations for,
        and one key,value pair for each sample annotation.

    !!! example
        ```python
        >>> conn = sql.get_sql_connection("test.db")
        >>> get_sample_annotations_by_variant(conn,42)
        >>> [
                {'sample_id': 1, 'variant_id': 42, 'gt': -1},
                {'sample_id': 2, 'variant_id': 42, 'gt': -1},
                {...},
                {'sample_id': 4, 'variant_id': 42, 'gt': -1},
                {'sample_id': 5, 'variant_id': 42, 'gt': -1},
                {'sample_id': 6, 'variant_id': 42, 'gt': -1},
                {'sample_id': 7, 'variant_id': 42, 'gt': -1}
            ]
        ```
    """
    conn.row_factory = sqlite3.Row
    return [
        dict(data)
        for data in conn.execute(
            f"SELECT * FROM sample_has_variant WHERE variant_id = {variant_id}"
        )
    ]


def update_sample(conn: sqlite3.Connection, sample: dict):
    """Updates sample record with sample as the new data

    Args:
        conn (sqlite3.Connection): Sqlite3 connection
        sample (dict): Sample data to update. Must have an 'id' key.

    !!! example
        ```python
        >>> conn = sql.get_sql_connection("test.db")
        >>> sample = {
                id : 3 #sample id
                name : "Boby",  #Name of sample
                family_id : "fam", # familly identifier
                father_id : 0, #father id, 0 if not
                mother_id : 0, #mother id, 0 if not
                sex : 0 #sex code ( 1 = male, 2 = female, 0 = unknown)
                phenotype: 0 #( 1 = control , 2 = case, 0 = unknown)
            }
        >>> sql.update_sample(conn,sample)
        ```

    !!! todo "To do"
        Raise exception if sample doesn't contain the 'id' key
    """
    if "id" not in sample:
        logging.debug("sample id is required")
        return

    sql_set = []
    sql_val = []

    for key, value in sample.items():
        if key != "id":
            sql_set.append(f"`{key}` = ? ")
            sql_val.append(value)

    query = (
        "UPDATE samples SET " + ",".join(sql_set) + " WHERE id = " + str(sample["id"])
    )
    conn.execute(query, sql_val)
    conn.commit()
