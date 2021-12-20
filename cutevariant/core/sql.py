"""Module to bring together all the SQL related functions

    To read and write the sqlite database with the schema described here.

    There are 4 resources in the databases : 

    - variants ( variant table and annotations)
    - samples 
    - fields
    - wordsets 
    - selections

    Each CRUD operations respect the following naming : 

    - get_fields(conn, ...)
    - get_field(conn, id)
    - insert_fields(generator) # Insert new elements 
    - insert_field(id) # Insert one elements 
    - delete_fields(generator) # Remove many fields 
    - delete_field(id) # remove a field 
    - update_fields(generator) # update fields 
    - update_field() 


    get_variant(id)   #   récupérer un variant
    get_variants(**option) # récupérer des variants 

    insert_variants({}) # Insert many variants 

    insert_variants([sdf]) # 


    insert_variants_async() # async




    update_variant(variant)  # Update un variant
    update_variants(id, variants) # update des variants 

    delete_selection() ==> 

    delete_selection_by_name()  ==> 


    delete_selection({"id": 34})

    delete_selection(id=23)

    delete_selection(name="324")
    delete_selection({name:"3324"})



    remove_variant(id)

    The module contains also QueryBuilder class to build complexe variant query based
    on filters, columns and selections.

    Example::

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

Attributes:
    delete_selection_by_name (TYPE): Description
    delete_set_by_name (TYPE): Description

"""

# Standard imports
import sqlite3
from collections import defaultdict
import re
import logging
from sqlite3.dbapi2 import DatabaseError
import typing
from pkg_resources import parse_version
from functools import partial, lru_cache
import itertools as it
import numpy as np
import json
import typing

# Custom imports
import cutevariant.commons as cm
import cutevariant.core.querybuilder as qb
from cutevariant.core.sql_aggregator import StdevFunc
from cutevariant import LOGGER



# ==================================================
#
#  SQL HELPER 
#
#===================================================

def get_sql_connection(filepath:str) -> sqlite3.Connection:
    """Open a SQLite database and return the connection object

    Args:
        filepath (str): sqlite filepath

    Returns:
        sqlite3.Connection: Sqlite3 Connection
            The connection is initialized with `row_factory = Row`.
            So all results are accessible via indexes or keys.
            The connection also supports
            - REGEXP function
            - DESCRIBE_QUANT aggregate
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
    connection.create_aggregate("STD", 1, StdevFunc)

    if LOGGER.getEffectiveLevel() == logging.DEBUG:
        # Enable tracebacks from custom functions in DEBUG mode only
        sqlite3.enable_callback_tracebacks(True)

    return connection


def get_database_file_name(conn:sqlite3.Connection) -> str:
    """Return sqlite filename name 
    
    Args:
        conn (sqlite3.Connection): Sqlite3 connection
    
    Returns:
        str: Path of the salite database
    """
    return conn.execute("PRAGMA database_list").fetchone()["file"]


def table_exists(conn: sqlite3.Connection, name: str) -> bool:
    """Return True if table exists

    Args:
        conn (sqlite3.Connection): Sqlite3 connection
        name (str): Table name

    Returns:
        bool: True if table exists
    """
    c = conn.cursor()
    c.execute(f"SELECT name FROM sqlite_master WHERE name = '{name}'")
    return c.fetchone() != None


def drop_table(conn, table_name:str):
    """Drop the given table

    Args:
        conn (sqlite3.connection): Sqlite3 connection
        table_name (str): sqlite table name
    """
    cursor = conn.cursor()
    cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
    conn.commit()


def clear_table(conn: sqlite3.Connection, table_name:str):
    """Clear content of the given table

    Args:
        conn (sqlite3.Connection): Sqlite3 Connection
        table_name (str): sqlite table name
    """
    cursor = conn.cursor()
    cursor.execute(f"DELETE  FROM {table_name}")
    conn.commit()


def get_table_columns(conn: sqlite3.Connection, table_name:str):
    """Return the list of columns for the given table

    Args:
        conn (sqlite3.Connection): Sqlite3 Connection
        table_name (str): sqlite table name

    Returns:
        Columns description from table_info
        ((0, 'chr', 'str', 0, None, 1 ... ))

    References:
        used by async_insert_many_variants() to build queries with placeholders
    """
    return [
        c[1] for c in conn.execute(f"pragma table_info({table_name})") if c[1] != "id"
    ]


def count_query(conn: sqlite3.Connection, query:str) -> int:
    """Count elements from the given query or table
    
    Args:
        conn (sqlite3.Connection): Sqlite3.Connection
        query (str): SQL Query
    
    Returns:
        int: count of records 
    """
    return conn.execute(f"SELECT COUNT(*) as count FROM ({query})").fetchone()[0]


# Helper functions. TODO: move them somewhere more relevant


def clear_lru_cache():
    get_fields.cache_clear()
    get_field_by_category.cache_clear()


# Statistical data


def get_stats_info(conn, field, source="variants", filters={}):
    pass


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
    query = qb.build_sql_query(conn, [field], source, filters, limit=None)

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


def get_indexed_fields(conn: sqlite3.Connection) -> typing.List[tuple]:
    """Returns, for this connection, a list of indexed fields
    Each element of the returned list is a tuple of (category,field_name)

    Args:
        conn (sqlite3.Connection): Sqlite3 connection

    Returns:
        typing.List[tuple]: (category, field_name) of all the indexed fields
    """
    indexed_fields = [
        dict(res)["name"]
        for res in conn.execute("SELECT name FROM sqlite_master WHERE type='index'")
    ]
    result = []
    find_indexed = re.compile(r"idx_(variants|annotations|samples)_(.+)")
    for index in indexed_fields:
        matches = find_indexed.findall(index)
        if matches and len(matches[0]) == 2:
            category, field_name = matches[0]
            result.append((category, field_name))
    return result

def remove_indexed_field(conn: sqlite3.Connection, category: str, field_name: str):
    conn.execute(f"DROP INDEX IF EXISTS idx_{category}_{field_name}")
    conn.commit()



def create_indexes(
    conn: sqlite3.Connection,
    indexed_variant_fields=None,
    indexed_annotation_fields=None,
    indexed_sample_fields=None,
):
    """Create extra indexes on tables

    Args:
        conn (sqlite3.Connection): Sqlite3 Connection

    Note:
        This function must be called after batch insertions.
        You should use this function instead of individual functions.

    """

    create_selections_indexes(conn)

    create_variants_indexes(conn, indexed_variant_fields)

    create_samples_indexes(conn, indexed_sample_fields)

    try:
        # Some databases have not annotations table
        create_annotations_indexes(conn, indexed_annotation_fields)
    except sqlite3.OperationalError as e:
        LOGGER.debug("create_indexes:: sqlite3.%s: %s", e.__class__.__name__, str(e))



# ==================================================
#
#  CRUD Operation  
#
#===================================================
 
## Project table =============================================================

def create_table_project(conn: sqlite3.Connection):
    """Create the table "projects" and insert project name and reference genome
    Args:
        conn (sqlite3.Connection): Sqlite3 Connection
        project (dict): A key value dict. Should contains project_name and reference. 
    """

    conn.execute("CREATE TABLE projects (key TEXT PRIMARY KEY, value TEXT)")
    conn.commit()

def update_project(conn: sqlite3.Connection, project: dict):
    """Update project 
    
    Args:
        conn (sqlite3.Connection): Sqlite3 Connection
        project (dict): Description
    """
    conn.executemany(
        "INSERT OR REPLACE INTO projects (key, value) VALUES (?, ?)", list(project.items())
    )
    conn.commit()


def get_project(conn: sqlite3.Connection) -> dict:
    """Get project 
    
    Args:
        conn (sqlite3.Connection): Sqlite3 Connection
    
    Returns:
        dict: Project information as key:value dictionnary
    """
    g = (dict(data) for data in conn.execute("SELECT key, value FROM projects"))
    return {data["key"]: data["value"] for data in g}


## metadatas table =============================================================


def create_table_metadatas(conn: sqlite3.Connection):
    """Create table metdatas

    Args:
        conn (sqlite3.Connection): Sqlite3 Connection
    """

    conn.execute(
        "CREATE TABLE metadatas (key TEXT PRIMARY KEY, value TEXT)"
    )


def update_metadatas(conn: sqlite3.Connection, metadatas:dict):
    """Populate metadatas with a key/value dictionnaries
    
    Args:
        conn (sqlite3.Connection): Sqlite3 Connection
        metadatas (dict, optional)
    """
    if metadatas:
        cursor = conn.cursor()
        cursor.executemany(
            "INSERT OR REPLACE INTO metadatas (key,value) VALUES (?,?)", list(metadatas.items())
        )

        conn.commit()


def get_metadatas(conn: sqlite3.Connection) -> dict:
    """Return a dictionary of metadatas

    Returns:
        [dict]: matadata fieldname as keys
    """
    conn.row_factory = sqlite3.Row
    g = (dict(data) for data in conn.execute("SELECT key, value FROM metadatas"))
    return {data["key"]: data["value"] for data in g}


## selections & sets tables ====================================================

def create_table_selections(conn: sqlite3.Connection):
    """Create the table "selections" and association table "selection_has_variant"

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
        variant_id INTEGER NOT NULL REFERENCES variants(id) ON DELETE CASCADE,
        selection_id INTEGER NOT NULL REFERENCES selections(id) ON DELETE CASCADE,
        PRIMARY KEY (variant_id, selection_id)
        )"""
    )
    conn.commit()


def create_selections_indexes(conn: sqlite3.Connection):
    """Create indexes on the "selections" table

    Args:
        conn (sqlite3.Connection): Sqlite3 Connection

    Note:
        * This function should be called after batch insertions.
        * This function ensures the unicity of selections names.
    """
    conn.execute("CREATE UNIQUE INDEX idx_selections ON selections (name)")


def create_selection_has_variant_indexes(conn: sqlite3.Connection):
    """Create indexes on "selection_has_variant" table

    For joins between selections and variants tables

    Reference:
        * create_selections_indexes()
        * insert_selection()

    Args:
        conn (sqlite3.Connection/sqlite3.Cursor): Sqlite3 connection
    """
    conn.execute(
        "CREATE INDEX `idx_selection_has_variant` ON selection_has_variant (`selection_id`)"
    )


def insert_selection(conn:sqlite3.Connection, query: str, name="no_name", count=0) -> int:
    """Insert one record in the selection table and return the last insert id. 
    This function is used by `insert_selection_from_[source|bed|sql]` functions. 

    Do not use this function. Use insert_selection_from_[source|bed|sql].

    Args:
        conn (sqlite3.Connection): Sqlite3 Connection.
        query (str): a VQL query
        name (str, optional): Name of the selection
        count (int, optional): Count of variant in the selection

    Returns:
        int: Return last rowid

    See Also:
        create_selection_from_sql()
        create_selection_from_source()
        create_selection_from_bed()

    Warning:
        This function does a commit !


    """
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO selections (name, count, query) VALUES (?,?,?)",
        (name, count, query),
    )
    
    conn.commit()

    return cursor.lastrowid


def insert_selection_from_source(
    conn: sqlite3.Connection,
    name: str,
    source: str = "variants",
    filters=None,
    count=None,
) -> int:
    """Create a selection from another selection. 
    This function create a subselection from another selection by applying filters. 

    Examples:

    Create a subselection from "variants" with variant reference equal "A".  

        insert_selection_from_source(
            conn,
            "new selection",
            "variants",
            {"$and": [{"ref": "A"}]},
            123
        )

    Args:
        conn (sqlite3.connection): Sqlite3 connection
        name (str): Name of selection
        source (str): Source to select from
        filters (dict/None, optional): a filters to create selection
        count (int/None, optional): Pre-computed variant count. If None, it does the computation

    Returns:
        selection_id, if lines have been inserted; None otherwise (rollback).
    """

    cursor = conn.cursor()

    filters = filters or {}
    sql_query = qb.build_sql_query(
        conn,
        fields=[],
        source=source,
        filters=filters,
        limit=None,
    )
    vql_query = qb.build_vql_query(fields=["id"], source=source, filters=filters)

    # Compute query count
    # TODO : this can take a while .... need to compute only one from elsewhere
    if count is None:
        count = count_query(conn, sql_query)

    # Create selection
    selection_id = insert_selection(conn, vql_query, name=name, count=count)

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

    # Optimized only for the creation of a selection from set operations
    # variant_id is the only useful column here
    q = f"""
    INSERT INTO selection_has_variant
    SELECT DISTINCT id, {selection_id} FROM ({sql_query})
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


def insert_selection_from_sql(
    conn: sqlite3.Connection, query: str, name: str, count=None, from_selection=False
) -> int:
    """Create a selection from sql variant query.

    The SQL variant query must have all variant.id to import into the selection

    insert_selection_from_sql(
        conn,
        "SELECT id FROM variants WHERE ref ='A'",
        "my selection",
        324
    )

    Args:
        conn (sqlite3.connection): Sqlite3 connection
        query (str): SQL query that select all variant ids. See `from_selection`
        name (str): Name of selection
        count (int/None, optional): Precomputed variant count
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
        count = count_query(conn, query)

    # Create selection
    selection_id = insert_selection(conn, query, name=name, count=count)

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
    delete_selection(conn, selection_id)
    return None


def insert_selection_from_bed(
    conn: sqlite3.Connection, source: str, target: str, bed_intervals
)->int:
    """Create a new selection based on the given intervals taken from a BED file

    Variants whose positions are contained in the intervals specified by the
    BED file will be referenced into the table selection_has_variant under
    a new selection.

    Args:
        conn (sqlite3.connection): Sqlite3 connection
        source (str): Selection name (source); Ex: "variants" (default)
        target (str): Selection name (target)
        bed_intervals (list/generator [dict]): List of intervals
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
        source_query = "SELECT DISTINCT variants.id AS variant_id FROM variants"
    else:
        source_query = f"""
        SELECT DISTINCT variants.id AS variant_id FROM variants
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

    return insert_selection_from_sql(conn, query, target, from_selection=True)


def get_selections(conn: sqlite3.Connection)->typing.List[dict]:
    """Get selections from "selections" table

    Args:
        conn (sqlite3.connection): Sqlite3 connection

    Yield:
        Dictionnaries with as many keys as there are columnsin the table.

    Example::
        {"id": ..., "name": ..., "count": ..., "query": ...}

    """
    conn.row_factory = sqlite3.Row
    return (dict(data) for data in conn.execute("SELECT * FROM selections"))


def delete_selection(conn: sqlite3.Connection, selection_id: int):
    """Delete the selection with the given id in the "selections" table

    Args:
        conn (sqlite3.Connection): Sqlite connection
        selection_id (int): id from selection table

    Returns:
        int: Number of rows affected
    """

    # Ignore if it is the first selection name aka 'variants'
    if selection_id <= 1:
        return None

    cursor = conn.cursor()

    cursor.execute("DELETE FROM selections WHERE rowid = ?", (selection_id,))
    conn.commit()
    return cursor.rowcount


def delete_selection_by_name(conn: sqlite3.Connection, name: str):
    """Delete data in "selections" 

    Args:
        conn (sqlit3.Connection): sqlite3 connection
        name (str): Selection
    Returns:
        int: Number of rows affected
    """

    if name == "variants":
        LOGGER.error("Cannot remove the default selection 'variants'")
        return

    cursor = conn.cursor()
    cursor.execute(f"DELETE FROM selections WHERE name = ?", (name,))
    conn.commit()
    return cursor.rowcount


def update_selection(conn: sqlite3.Connection, selection: dict):
    """Update the name and count of a selection with the given id

    Args:
        conn (sqlite3.Connection): sqlite3 Connection
        selection (dict): key/value data

    Returns:
        int: last rowid
    """
    cursor = conn.cursor()
    conn.execute(
        "UPDATE selections SET name=:name, count=:count WHERE id = :id", selection
    )
    conn.commit()
    return cursor.rowcount


## wordsets table ===============================================================


def create_table_wordsets(conn: sqlite3.Connection):
    """Create the table "sets"

    This table stores variants selection saved by the user:
        - name: name of the set of variants
        - value: number of variants concerned by this set

    TODO: Denormalization of this table **WILL** BE a problem in the future...
        But i'm fed up of these practices.

    TODO: for now the one to many relation is not implemented

    Args:
        conn (sqlite3.Connection): Sqlite3 Connection
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


def _sanitize_words(words):
    """Return a set of cleaned words

    See Also:
        - :meth:`import_wordset_from_file`
        - :meth:`cutevariant.gui.plugins.word_set.widgets.WordListDialog.load_file`
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


def insert_wordset_from_file(conn: sqlite3.Connection, wordset_name, filename):
    r"""Create Word set from the given file

    Args:
        wordset_name: Name of the Word set
        filename: File to be imported, we expect 1 word per line.

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
    with open(filename, "r") as f_h:
        data = _sanitize_words(f_h)

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


def insert_wordset_from_list(conn: sqlite3.Connection, wordset_name, words: list):
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

    data = _sanitize_words(words)

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


def insert_wordset_from_intersect(conn: sqlite3.Connection, name: str, wordsets: list):
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
    cursor = conn.cursor()
    cursor.execute(query)
    conn.commit()
    return cursor.rowcount


def insert_wordset_from_union(conn, name: str, wordsets=[]):
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
    cursor = conn.cursor()
    cursor.execute(query)
    conn.commit()
    return cursor.rowcount


def insert_wordset_from_subtract(conn, name: str, wordsets=[]):
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
    cursor = conn.cursor()
    cursor.execute(query)
    conn.commit()
    return cursor.rowcount

def get_wordsets(conn:sqlite3.Connection):
    """Return the number of words per word set stored in DB

    Returns:
        generator[dict]: Yield dictionaries with `name` and `count` keys.
    """
    for row in conn.execute(
        "SELECT name, COUNT(*) as 'count' FROM wordsets GROUP BY name"
    ):
        yield dict(row)


def get_wordset_by_name(conn, wordset_name):
    """Return generator of words in the given word set

    Returns:
        generator[str]: Yield words of the word set.
    """
    for row in conn.execute(
        "SELECT DISTINCT value FROM wordsets WHERE name = ?", (wordset_name,)
    ):
        yield dict(row)["value"]



def delete_wordset_by_name(conn: sqlite3.Connection, name: str):
    """Delete data in "selections" or "sets" tables with the given name

    Args:
        conn (sqlit3.Connection): sqlite3 connection
        name (str): Selection/set name
        table_name (str): Name of the table concerned by the deletion
    Returns:
        int: Number of rows affected
    """

    cursor = conn.cursor()
    cursor.execute(f"DELETE FROM wordsets WHERE name = ?", (name,))
    conn.commit()
    return cursor.rowcount


## Operations on sets of variants ==============================================

def intersect_variants(query1, query2, **kwargs):
    """Get the variants obtained by the intersection of 2 queries

    Try to handle precedence of operators.
    - The precedence of UNION and EXCEPT are similar, they are processed from
    left to right.
    - Both of the operations are fulfilled before INTERSECT operation,
    i.e. they have precedence over it.

    """
    return f"""SELECT * FROM ({query1} INTERSECT {query2})"""


def union_variants(query1, query2, **kwargs):
    """Get the variants obtained by the union of 2 queries"""
    return f"""{query1} UNION {query2}"""


def subtract_variants(query1, query2, **kwargs):
    """Get the variants obtained by the difference of 2 queries"""
    return f"""{query1} EXCEPT {query2}"""


## fields table ================================================================


def create_table_fields(conn: sqlite3.Connection):
    """Create the table "fields"

    This table contain fields. A field is a column with its description and type;
    it can be choose by a user to build a Query
    Fields are the columns of the tables: variants, annotations and sample_has_variant.
    Fields are extracted from reader objects and are dynamically constructed.

    variants:
    Chr,pos,ref,alt, filter, qual, dp, af, etc.

    annotations:
    Gene, transcrit, etc.

    sample_has_variant:
    Genotype

    :param conn: sqlite3.connect
    """
    cursor = conn.cursor()
    cursor.execute(
        """CREATE TABLE fields
        (id INTEGER PRIMARY KEY, name TEXT, category TEXT, type TEXT, description TEXT, UNIQUE(name, category))
        """
    )
    conn.commit()


def insert_field(
    conn, name="no_name", category="variants", field_type="text", description=""
):
    """Insert one fields 

    This is a shortcut and it calls insert_fields with one element 

    Args:
        conn (sqlite.Connection): sqlite Connection
        name (str, optional): fields name. Defaults to "no_name".
        category (str, optional): fields table. Defaults to "variants".
        field_type (str, optional): type of field in python (str,int,float,bool). Defaults to "text".
        description (str, optional): field description   """    

    insert_fields(conn, [{"name":name, "category":category, "type":field_type, "description":description}])

def insert_fields(conn:sqlite3.Connection, data: list):
    """Insert multiple fields into "fields" table using one commit

    :param conn: sqlite3.connect
    :param data: list of field dictionnary

    :Examples:

        insert_many_fields(conn, [{name:"sacha", category:"variant", count: 0, description="a description"}])
        insert_many_fields(conn, reader.get_fields())

    .. seealso:: insert_field, abstractreader
    """
    cursor = conn.cursor()
    cursor.executemany(
        """
        INSERT OR REPLACE INTO fields (name,category,type,description)
        VALUES (:name,:category,:type,:description)
        """,
        data,
    )
    conn.commit()



def insert_only_new_fields(conn, data: list):
    """Insert in "fields" table the fields who did not already exist. 
    Add those fields as new columns in "variants", "annotations" or "samples" tables.

    :param conn: sqlite3.connect
    :param data: list of field dictionnary
    """
    get_fields.cache_clear()
    existing_fields = [(f["name"], f["category"]) for f in get_fields(conn)]
    new_data = [f for f in data if (f["name"], f["category"]) not in existing_fields]
    cursor = conn.cursor()
    cursor.executemany(
        """
        INSERT INTO fields (name,category,type,description)
        VALUES (:name,:category,:type,:description)
        """,
        new_data,
    )
    for field in new_data:
        cursor.execute(
            "ALTER TABLE %s ADD COLUMN %s %s" % (field["category"], field["name"], field["type"])
        )
    conn.commit()

#@lru_cache()
def get_fields(conn):
    """Get fields as list of dictionnary

    .. seealso:: insert_many_fields

    :param conn: sqlite3.connect
    :return: Tuple of dictionnaries with as many keys as there are columns
        in the table.
    :rtype: <tuple <dict>>
    """
    conn.row_factory = sqlite3.Row
    return tuple(dict(data) for data in conn.execute("SELECT * FROM fields"))


#@lru_cache()
def get_field_by_category(conn, category):
    """Get fields within a category

    :param conn: sqlite3.connect
    :param category: Category of field requested.
    :type category: <str>
    :return: Tuple of dictionnaries with as many keys as there are columns
        in the table. Dictionnaries are only related to the given field category.
    :rtype: <tuple <dict>>
    """
    return tuple(field for field in get_fields(conn) if field["category"] == category)


def get_field_by_name(conn, field_name: str):
    """Return field by its name

    .. seealso:: get_fields

    :param conn: sqlite3.connect
    :param field_name: field name
    :return: field record or None if not found.
    :rtype: <dict> or None
    """
    conn.row_factory = sqlite3.Row
    field_data = conn.execute(
        "SELECT * FROM fields WHERE name = ? ", (field_name,)
    ).fetchone()
    return dict(field_data) if field_data else None


def get_field_range(conn, field_name: str, sample_name=None):
    """Return (min,max) of field_name records

    :param conn: sqlite3.connect
    :param field_name: field name
    :param sample_name: sample name. mandatory for fields in the "samples" categories
    :return: (min, max) or None if the field can't be processed with mix/max functions.
    :rtype: tuple or None
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

    :param conn: sqlite3.connect
    :param field_name: Name of the field in DB.
    :param sample_name: sample name. Mandatory for fields in the "samples" categories
    :return: list of unique values (can be empty if the field is not found)
    :rtype: list
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


def create_table_annotations(conn: sqlite3.Connection, fields:typing.List[dict]):
    """Create "annotations" table which contains dynamics fields

    :param fields: Generator of SQL fields. Example of fields:

        .. code-block:: python

            ('allele str NULL', 'consequence str NULL', ...)
    :type fields: <generator>
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

    cursor.execute(
        f"""CREATE TABLE annotations (variant_id 
        INTEGER REFERENCES variants(id) ON UPDATE CASCADE,
         {schema})

        """
    )

    conn.commit()


def create_annotations_indexes(conn, indexed_annotation_fields=None):
    """Create indexes on the "annotations" table

    .. warning: This function must be called after batch insertions.

    :Example:

    .. code-block:: sql

        SELECT *, group_concat(annotations.rowid) FROM variants
        LEFT JOIN annotations ON variants.rowid = annotations.variant_id
        WHERE pos = 0
        GROUP BY chr,pos
        LIMIT 100
    """
    # Allow search on variant_id
    conn.execute(
        "CREATE INDEX IF NOT EXISTS `idx_annotations` ON annotations (`variant_id`)"
    )

    if indexed_annotation_fields is None:
        return
    for field in indexed_annotation_fields:

        LOGGER.debug(
            f"CREATE INDEX IF NOT EXISTS `idx_annotations_{field}` ON annotations (`{field}`)"
        )

        conn.execute(
            f"CREATE INDEX IF NOT EXISTS `idx_annotations_{field}` ON annotations (`{field}`)"
        )


def get_annotations(conn, variant_id: int):
    """Get variant annotation for the variant with the given id"""
    conn.row_factory = sqlite3.Row
    for annotation in conn.execute(
        f"SELECT * FROM annotations WHERE variant_id = {variant_id}"
    ):
        yield dict(annotation)


## variants table ==============================================================


def create_table_variants(conn: sqlite3.Connection, fields:typing.List[dict]):
    """Create "variants" and "sample_has_variant" tables which contains dynamics fields

    :Example:

        fields = get_fields()
        create_table_variants(conn, fields)

    .. seealso:: get_fields

    .. note:: "gt" field in "sample_has_variant" = Patient's genotype.
        - Patient without variant: gt = 0: Wild homozygote
        - Patient with variant in the heterozygote state: gt = -1: Heterozygote
        - Patient with variant in the homozygote state: gt = 2: Homozygote

        :Example of VQL query:
            SELECT chr, pos, genotype("pierre") FROM variants

    :param conn: sqlite3.connect
    :param fields: list of field dictionnary.
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


def create_variants_indexes(conn, indexed_fields={"pos", "ref", "alt"}):
    """Create indexes on the "variants" table

    .. warning:: This function must be called after batch insertions.

    :Example:

    .. code-block:: sql

        SELECT *, group_concat(annotations.rowid) FROM variants
        LEFT JOIN annotations ON variants.rowid = annotations.variant_id
        WHERE pos = 0
        GROUP BY chr,pos
        LIMIT 100
    """
    # Complementary index of the primary key (sample_id, variant_id)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS `idx_sample_has_variant` ON sample_has_variant (`variant_id`, `sample_id`)"
    )

    for field in indexed_fields:
        conn.execute(
            f"CREATE INDEX IF NOT EXISTS `idx_variants_{field}` ON variants (`{field}`)"
        )


def get_variant(
    conn: sqlite3.Connection,
    variant_id: int,
    with_annotations=False,
    with_samples=False,
):
    r"""Get the variant with the given id

    TODO: with_annotations, with_samples are quite useless and not used for now

    Args:
        conn (sqlite3.Connection): sqlite3 connection
        variant_id (int): Database id of the variant
        with_annotations (bool, optional): Add annotations items. Default is True
        with_samples (bool, optional): add samples items. Default is True

    Returns:
        dict: A variant item with all fields in "variants" table;
            \+ all fields of annotations table if `with_annotations` is True;
            \+ all fields of sample_has_variant associated to all samples if
            `with_samples` is True.
            Example:

            .. code-block:: python

                {
                    variant fields as keys...,
                    "annotations": dict of annotations fields as keys...,
                    "samples": dict of samples fields as keys...,
                }

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
    """Update variant data

    Used by widgets to save various modifications in a variant.

    Args:
        variant (dict): Fields as keys; values as values.
            'id' key is expected to set the variant.

    Raises:
        KeyError if 'id' key is not in the given variant
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
    """Get the number of variants in the "variants" table"""
    return count_query(conn, "variants")


def get_variants(
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

    # TODO : rename as get_variant_as_tables ?

    query = qb.build_sql_query(
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


def get_variants_tree(
    conn: sqlite3.Connection,
    **kwargs,
):
    pass
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


def insert_variants_async(conn:sqlite3.Connection, data: list, total_variant_count=None, yield_every=3000):
    """Insert many variants from data into variants table

    :param conn: sqlite3.connect
    :param data: list of variant dictionnary which contains same number of key than fields numbers.
    :param total_variant_count: total variant count, to compute progression
    :return: Yield a tuple with progression and message.
        Progression is 0 if total_variant_count is not set.
    :rtype: <generator <tuple <int>, <str>>


    :Example:

        insert_many_variant(conn, [{chr:"chr1", pos:24234, alt:"A","ref":T }])
        insert_many_variant(conn, reader.get_variants())

    .. warning:: Using reader, this can take a while
    .. todo:: with large dataset, need to cache import
    .. todo:: handle insertion errors...
    .. seealso:: abstractreader

    .. warning:: About using INSERT OR IGNORE: They avoid the following errors:

        - Upon insertion of a duplicate key where the column must contain
          a PRIMARY KEY or UNIQUE constraint
        - Upon insertion of NULL value where the column has
          a NOT NULL constraint.
          => This is not recommended
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


def insert_variants(conn, data, **kwargs):
    """Wrapper for debugging purpose"""
    for _, _ in insert_variants_async(conn, data, kwargs):
        pass


def update_variants_async(conn, data, old_samples, total_variant_count=None, yield_every=3000):
    """Insert many variants from data into variants table

    :param conn: sqlite3.connect
    :param data: list of variant dictionnary which contains same number of key than fields numbers.
    :param old_samples: already existing samples in "samples" table as a list of dictionaries {id, name}
    :param total_variant_count: total variant count, to compute progression
    :return: Yield a tuple with progression and message.
        Progression is 0 if total_variant_count is not set.
    :rtype: <generator <tuple <int>, <str>>

    TODO: remove indexes before update
    TODO: rebuild them after
    """
    def delete_selection_index(conn):
        """Ugly bugfix that is needed because everything tries to create a default variant
        selection and cutevariant crashes if one already exists"""
        cursor = conn.cursor()
        cursor.execute("DELETE FROM selections WHERE name = '%s'" % (cm.DEFAULT_SELECTION_NAME,))
        conn.commit()

    def remove_nonexisting_columns(conn, data: list):
        """Remove from new data columns that don't exist in variants and annotations tables.
        Alternative: add missing columns instead.
        
        04/11/2021 Update: the alternative was implemented.
        """
        var_cols = get_table_columns(conn, "variants")
        ann_cols = get_table_columns(conn, "annotations")
        samples_cols = get_table_columns(conn, "sample_has_variant")
        samples_cols += ["name"] #needed for update_sample_has_variant(args)
        filtered_data = []
        for var in data:
            filtered_var = {k: var[k] for k in var if k in var_cols }

            filtered_ann = []
            if "annotations" in var.keys():
                for ann in var["annotations"]:
                    ann = {k: ann[k] for k in ann if k in ann_cols}
                    filtered_ann.append(ann)
                filtered_var["annotations"] = filtered_ann

            filtered_samples = []
            if "samples" in var.keys():
                for s in var["samples"]:
                    s = {k: s[k] for k in s if k in samples_cols}
                    filtered_samples.append(s)
                filtered_var["samples"] = filtered_samples

            filtered_data.append(filtered_var)
        return filtered_data

    def build_unique_keys(data: list):
        """Associate variant data to a unique key to identify alreaydy inserted variants
        :param data: [{var1 dict}, {var2 dict}]
        :return: {chr_pos_ref_alt1 : {var1 dict}, chr_pos_ref_alt2: {var2 dict}}
        """
        id_dict = {}
        for var in data:
            id = "_".join([str(var[k]) for k in ("chr", "pos", "ref", "alt")])
            id_dict[id] = var
        return id_dict

    def identify_existing_variants(existing_var: dict, data_var: dict):
        """
        :return: 1) a dict linking new variants chr_pos_ref_alt keys 
                    to already inserted variants database IDs that will be updated
                 2) a list of variant data that are new in the database
                    and can be inserted with the usual function
        """
        update_dict = {}
        new_data = []
        for k in data_var.keys():
            if k in existing_var.keys():
                update_dict[k] = existing_var[k]["id"]
            else:
                new_data.append(data_var[k])
        return update_dict, new_data

    def async_update_variant(conn, variant: dict, cursor):
        """Adapted from update_variant(args), adding an arg to pass the cursor"""
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
        cursor.execute(query, values)
        return cursor

    def update_annotation(conn, variant_id: int, var_annotations: dict, cursor):
        """
        variant_id is not a unique primary key here
        Chosen solution: remove existing annotations for the variant,
        then insert the new ones.
        """
        conn.execute(
                f"DELETE FROM annotations WHERE variant_id = {variant_id}"
            )

        ann_columns = get_table_columns(conn, "annotations")
        anns = []

        for ann in var_annotations:
            default_values = defaultdict(lambda: None, ann)
            ann_value = [variant_id]
            ann_value += [default_values[i] for i in ann_columns[1:]]
            anns.append(ann_value)

        placeholders = ",".join(["?"] * len(ann_columns))
        q = f"INSERT OR REPLACE INTO annotations VALUES ({placeholders})"
        # cursor = conn.cursor()
        cursor.executemany(q, anns)
        # conn.commit()
        return cursor

    def update_sample_has_variant(conn, variant_id: int, var_samples: dict, cursor):
        """
        Adapted from async_insert_many_variants
        """
        samples_id_mapping = dict(conn.execute("SELECT name, id FROM samples"))
        sample_columns = get_table_columns(conn, "sample_has_variant")
        samples = []
        for sample in var_samples:
            sample_id = samples_id_mapping[sample["name"]]
            default_values = defaultdict(lambda: None, sample)
            sample_value = [sample_id, variant_id]
            sample_value += [default_values[i] for i in sample_columns[2:]]
            samples.append(sample_value)

        placeholders = ",".join(["?"] * len(sample_columns))
        q = f"INSERT OR REPLACE INTO sample_has_variant VALUES ({placeholders})"
        # cursor = conn.cursor()
        cursor.executemany(q, samples)
        # conn.commit()
        return cursor

    def fully_update_variant(conn, variant: dict, cursor):
        cursor = async_update_variant(conn, 
            {k: variant[k] for k in variant if k not in ("samples", "annotations")},
            cursor
        )
        if "annotations" in variant.keys():
            cursor = update_annotation(conn, variant["id"], variant["annotations"], cursor)
        if "samples" in variant.keys():
            cursor = update_sample_has_variant(conn, variant["id"], variant["samples"], cursor)
        return cursor

    # data = remove_nonexisting_columns(conn, data)

    existing_var = [v for v in get_variants(conn,
                                ["id", "chr", "pos", "ref", "alt"],
                                limit = get_variants_count(conn))]
    existing_var_dict = build_unique_keys(existing_var)
    data_var_dict = build_unique_keys(data)
    update_dict, new_data = identify_existing_variants(existing_var_dict, data_var_dict)

    previous_max_var_id = [dict(res) for res in conn.execute(f"SELECT max(id) FROM variants")][0]["max(id)"]

    #New variants can be inserted with the usual method
    delete_selection_index(conn)
    for percent, msg in insert_variants_async(conn, 
                                        new_data, 
                                        total_variant_count=len(new_data), 
                                        yield_every=yield_every):
        yield percent, msg
    #the usual insertion method does not update old samples with new variants
    add_new_variants_to_old_samples(conn, old_samples, new_data, previous_max_var_id)

    #For previously existing variants, update variant, annotation and sample_has_variant tables
    variant_count = 0
    cursor = conn.cursor()
    total_update_count = len(update_dict)
    #using a separate list to iterate because keys will be changed during the loop
    original_data_keys = data_var_dict.keys()
    for k in original_data_keys:
        if k in update_dict.keys():
            data_var_dict[k]["id"] = update_dict[k]
            cursor = fully_update_variant(conn, data_var_dict[k], cursor)
            variant_count += 1
            if variant_count % yield_every == 0:
                progress = variant_count / total_update_count * 100
                yield progress, f"{variant_count} variants updated."
    yield 97, f"{variant_count} variant(s) has been updated."

    #Correct default selection to account for new number of variants
    cursor.execute("DELETE FROM selections WHERE name = '%s'" % (cm.DEFAULT_SELECTION_NAME,))
    conn.commit()
    insert_selection(
        conn, "", name=cm.DEFAULT_SELECTION_NAME, count=get_variants_count(conn)
    )

def update_variants(conn, data, **kwargs):
    """Wrapper for debugging purpose"""
    for _, _ in update_variants_async(conn, data, kwargs):
        pass

def get_variant_as_group(
    conn,
    groupby: str,
    fields: list,
    source: str,
    filters: dict,
    order_by_count=True,
    order_desc=True,
    limit=50,
):

    order_by = "count" if order_by_count else f"`{groupby}`"
    order_desc = "DESC" if order_desc else "ASC"

    subquery = qb.build_sql_query(
        conn,
        fields=fields,
        source=source,
        filters=filters,
        limit=None,
    )

    query = f"""SELECT `{groupby}`, COUNT(`{groupby}`) AS count
    FROM ({subquery}) GROUP BY `{groupby}` ORDER BY {order_by} {order_desc} LIMIT {limit}"""
    for i in conn.execute(query):
        res = dict(i)
        res["field"] = groupby
        yield res


## samples table ===============================================================


def create_table_samples(conn, fields=[]):
    """Create samples table

    :param conn: sqlite3.connect
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
        phenotype INTEGER DEFAULT 0,
        UNIQUE (name, family_id)
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


def create_samples_indexes(conn, indexed_samples_fields=None):
    """Create indexes on the "samples" table"""
    if indexed_samples_fields is None:
        return

    for field in indexed_samples_fields:
        conn.execute(
            f"CREATE INDEX IF NOT EXISTS `idx_samples_{field}` ON sample_has_variant (`{field}`)"
        )


def insert_sample(conn, name="no_name"):
    """Insert one sample in samples table (USED in TESTS)

    :param conn: sqlite3.connect
    :return: Last row id
    :rtype: <int>
    """
    cursor = conn.cursor()
    cursor.execute("INSERT INTO samples (name) VALUES (?)", [name])
    conn.commit()
    return cursor.lastrowid


def insert_samples(conn, samples: list):
    """Insert many samples at a time in samples table.
    Set genotype to -1 in sample_has_variant for all pre-existing variants.

    :param samples: List of samples names
        .. todo:: only names in this list ?
    :type samples: <list <str>>
    """
    cursor = conn.cursor()
    cursor.executemany(
        "INSERT INTO samples (name) VALUES (?)", ((sample,) for sample in samples)
    )
    conn.commit()


def insert_many_new_samples(conn, samples: list):
    """Insert new samples when adding a new vcf to a project

    :param samples: List of samples names
        .. todo:: only names in this list ?
    :type samples: <list <str>>
    """
    cursor = conn.cursor()
    cursor.executemany(
        "INSERT INTO samples (name) VALUES (?)", ((sample,) for sample in samples)
    )
    conn.commit()


def insert_only_new_samples(conn, samples: list):
    """Insert many samples at a time in samples table, except already inserted samples.

    :param samples: List of samples names
        .. todo:: only names in this list ?
    :type samples: <list <str>>
    """
    new_samples = [v for v in samples if v not in set([s["name"] for s in get_samples(conn)])]
    cursor = conn.cursor()
    cursor.executemany(
        "INSERT INTO samples (name) VALUES (?)", 
        ((sample,) for sample in new_samples)
    )

    #update sample_has_variant with new samples, setting everything to NULL (-1 for genotype)
    new_ids = [s["id"] for s in get_samples(conn) if s["name"] in new_samples]
    if "gt" in get_table_columns(conn, "sample_has_variant"):
        cursor.executemany(
            "INSERT INTO sample_has_variant (sample_id, variant_id, gt) VALUES (?,?,?)", 
            ((int(sample_id), int(var["id"]), "-1") 
                for sample_id in new_ids 
                for var in get_variants(conn, ["id"], limit = get_variants_count(conn))
            )
        )
    else:
        cursor.executemany(
            "INSERT INTO samples (sample_id, variant_id) VALUES (?,?)", 
            ((int(sample_id), int(var["id"])) 
                for sample_id in new_ids 
                for var in get_variants(conn, ["id"], limit = get_variants_count(conn))
            )
        )
    conn.commit()

def add_new_variants_to_old_samples(conn, old_samples: list, new_data, previous_max_var_id: int):
    """Update sample_has_variant for previously existing samples with newly inserted variants

    :param conn: sqlite connection
    :param old_samples: list of sample dict that were already present in "samples" table
    :param data_dict: dictionary {chr_pos_ref_alt: variant dict} ; variants in vcf used
                      for the update (may contain previously existing variants)
    :param previous_max_var_id: variant ids above this int correspond to newly inserted variants
    """
    samples_in_new_data = set()
    for v in new_data:
        if "samples" in v:
            for s in v["samples"]:
                samples_in_new_data.add(s["name"])
    samples_to_update = [s["id"] for s in old_samples if s["name"] not in samples_in_new_data]
    new_var_ids = [int(v["id"]) 
                        for v in get_variants(conn, ["id"], limit = get_variants_count(conn))
                        if int(v["id"]) > previous_max_var_id
                    ]

    if len(samples_to_update) > 0 and len(new_var_ids) > 0:
        cursor = conn.cursor()
        if "gt" in get_table_columns(conn, "sample_has_variant"):
            cursor.executemany(
                "INSERT INTO sample_has_variant (sample_id, variant_id, gt) VALUES (?,?,?)", 
                ((int(sample_id), int(var), "-1") 
                    for sample_id in samples_to_update 
                    for var in new_var_ids
                )
            )
        else:
            cursor.executemany(
                "INSERT INTO samples (sample_id, variant_id) VALUES (?,?)", 
                ((int(sample_id), int(var)) 
                    for sample_id in samples_to_update 
                    for var in new_var_ids
                )
            )
        conn.commit()




def get_samples(conn: sqlite3.Connection):
    """Get samples from sample table

    See Also: :meth:`update_sample`

    :param conn: sqlite3.conn
    :return: Generator of dictionnaries with as sample fields as values.
        :Example: ({'id': <unique_id>, 'name': <sample_name>})
    :rtype: <generator <dict>>
    """
    conn.row_factory = sqlite3.Row
    return (dict(data) for data in conn.execute("SELECT * FROM samples"))


def get_sample_annotations(conn, variant_id: int, sample_id: int):
    """Get samples for given sample id and variant id"""
    conn.row_factory = sqlite3.Row
    return dict(
        conn.execute(
            f"SELECT * FROM sample_has_variant WHERE variant_id = {variant_id} and sample_id = {sample_id}"
        ).fetchone()
    )


def get_sample_annotations_by_variant(conn, variant_id: int, fields=["gt"]):

    sql_fields = ",".join([f"sv.{f}" for f in fields])

    query = f"""SELECT samples.name, samples.phenotype, samples.sex, {sql_fields} FROM samples
    LEFT JOIN sample_has_variant sv 
    ON sv.sample_id = samples.id AND sv.variant_id = {variant_id}"""

    return (dict(data) for data in conn.execute(query))


def update_sample(conn: sqlite3.Connection, sample: dict):
    """Update sample record

    .. code-block:: python

        sample = {
            id : 3 #sample id
            name : "Boby",  #Name of sample
            family_id : "fam", # familly identifier
            father_id : 0, #father id, 0 if not
            mother_id : 0, #mother id, 0 if not
            sex : 0 #sex code ( 1 = male, 2 = female, 0 = unknown)
            phenotype: 0 #( 1 = control , 2 = case, 0 = unknown)
        }

    Args:
        conn (sqlite.connection): sqlite connection
        sample (dict): data
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
