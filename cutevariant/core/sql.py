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
import os
import getpass

from typing import Dict, List, Callable, Iterable
from datetime import datetime

# Custom imports
import cutevariant.constants as cst
import cutevariant.commons as cm

import cutevariant.core.querybuilder as qb
from cutevariant.core.sql_aggregator import StdevFunc
from cutevariant.core.reader import AbstractReader
from cutevariant.core.writer import AbstractWriter
from cutevariant.core.reader.pedreader import PedReader

from cutevariant import LOGGER

import cutevariant.constants as cst

DEFAULT_SELECTION_NAME = cst.DEFAULT_SELECTION_NAME or "variants"
SAMPLES_SELECTION_NAME = cst.SAMPLES_SELECTION_NAME or "samples"
CURRENT_SAMPLE_SELECTION_NAME = cst.CURRENT_SAMPLE_SELECTION_NAME or "current_sample"
LOCKED_SELECTIONS = [DEFAULT_SELECTION_NAME, SAMPLES_SELECTION_NAME, CURRENT_SAMPLE_SELECTION_NAME]

PYTHON_TO_SQLITE = {
    "None": "NULL",
    "int": "INTEGER",
    "float": "REAL",
    "str": "TEXT",
    "bytes": "BLOB",
    "bool": "INTEGER",
}

SQLITE_TO_PYTHON = {
    "NULL": "None",
    "INTEGER": "int",
    "REAL": "float",
    "TEXT": "str",
    "BLOB": "bytes",
}

MANDATORY_FIELDS = [
    {
        "name": "chr",
        "type": "str",
        "category": "variants",
        "constraint": "DEFAULT 'unknown'",
        "description": "chromosom name",
    },
    {
        "name": "pos",
        "type": "int",
        "category": "variants",
        "constraint": "DEFAULT -1",
        "description": "variant position",
    },
    {
        "name": "ref",
        "type": "str",
        "category": "variants",
        "constraint": "DEFAULT 'N'",
        "description": "reference allele",
    },
    {
        "name": "alt",
        "type": "str",
        "category": "variants",
        "constraint": "DEFAULT 'N'",
        "description": "alternative allele",
    },
    {
        "name": "favorite",
        "type": "bool",
        "category": "variants",
        "constraint": "DEFAULT 0",
        "description": "favorite tag",
    },
    {
        "name": "comment",
        "type": "str",
        "category": "variants",
        "constraint": "DEFAULT ''",
        "description": "comment of variant",
    },
    {
        "name": "classification",
        "type": "int",
        "category": "variants",
        "constraint": "DEFAULT 0",
        "description": "ACMG score",
    },
    {
        "name": "tags",
        "type": "str",
        "category": "variants",
        "constraint": "DEFAULT ''",
        "description": "list of tags ",
    },
    {
        "name": "count_hom",
        "type": "int",
        "constraint": "DEFAULT 0",
        "category": "variants",
        "description": "Number of homozygous genotypes (1/1)",
    },
    {
        "name": "count_het",
        "type": "int",
        "constraint": "DEFAULT 0",
        "category": "variants",
        "description": "Number of heterozygous genotypes (0/1)",
    },
    {
        "name": "count_ref",
        "type": "int",
        "constraint": "DEFAULT 0",
        "category": "variants",
        "description": "Number of homozygous genotypes (0/0)",
    },
    {
        "name": "count_none",
        "type": "int",
        "constraint": "DEFAULT 0",
        "category": "variants",
        "description": "Number of none genotypes (./.)",
    },
    {
        "name": "count_tot",
        "type": "int",
        "constraint": "DEFAULT 0",
        "category": "variants",
        "description": "Number of genotypes (all)",
    },
    {
        "name": "count_var",
        "type": "int",
        "constraint": "DEFAULT 0",
        "category": "variants",
        "description": "Number of genotpyes heterozygous (0/1) or homozygous (1/1)",
    },
    {
        "name": "freq_var",
        "type": "float",
        "constraint": "DEFAULT 0",
        "category": "variants",
        "description": "Frequency of variants for samples with genotypes (0/1 and 1/1)",
    },
    {
        "name": "count_validation_positive",
        "type": "int",
        "constraint": "DEFAULT 0",
        "category": "variants",
        "description": "Number of validated genotypes",
    },
    {
        "name": "count_validation_negative",
        "type": "int",
        "constraint": "DEFAULT 0",
        "category": "variants",
        "description": "Number of rejected genotypes",
    },
    {
        "name": "count_validation_positive_sample_lock",
        "type": "int",
        "constraint": "DEFAULT 0",
        "category": "variants",
        "description": "Number of validated genotypes within validated samples",
    },
    {
        "name": "count_validation_negative_sample_lock",
        "type": "int",
        "constraint": "DEFAULT 0",
        "category": "variants",
        "description": "Number of rejected genotypes within validated samples",
    },
    {
        "name": "control_count_hom",
        "type": "int",
        "constraint": "DEFAULT 0",
        "category": "variants",
        "description": "Number of homozygous genotypes (0/0) in control",
    },
    {
        "name": "control_count_het",
        "type": "int",
        "constraint": "DEFAULT 0",
        "category": "variants",
        "description": "Number of homozygous genotypes (1/1) in control",
    },
    {
        "name": "control_count_ref",
        "type": "int",
        "constraint": "DEFAULT 0",
        "category": "variants",
        "description": "Number of heterozygous genotypes (1/0) in control",
    },
    {
        "name": "case_count_hom",
        "type": "int",
        "category": "variants",
        "constraint": "DEFAULT 0",
        "description": "Number of homozygous genotypes (1/1) in case",
    },
    {
        "name": "case_count_het",
        "type": "int",
        "category": "variants",
        "constraint": "DEFAULT 0",
        "description": "Number of heterozygous genotypes (1/0) in case",
    },
    {
        "name": "case_count_ref",
        "type": "int",
        "category": "variants",
        "constraint": "DEFAULT 0",
        "description": "Number of homozygous genotypes (0/0) in case",
    },
    {
        "name": "is_indel",
        "type": "bool",
        "constraint": "DEFAULT 0",
        "category": "variants",
        "description": "True if variant is an indel",
    },
    {
        "name": "is_snp",
        "type": "bool",
        "constraint": "DEFAULT 0",
        "category": "variants",
        "description": "True if variant is a snp",
    },
    {
        "name": "annotation_count",
        "type": "int",
        "constraint": "DEFAULT 0",
        "category": "variants",
        "description": "Number of transcript",
    },
    ## SAMPLES
    {
        "name": "classification",
        "type": "int",
        "constraint": "DEFAULT 0",
        "category": "samples",
        "description": "classification",
    },
    {
        "name": "comment",
        "type": "str",
        "constraint": "DEFAULT ''",
        "category": "samples",
        "description": "comment of variant",
    },
    {
        "name": "tags",
        "type": "str",
        "category": "samples",
        "constraint": "DEFAULT ''",
        "description": "list of tags ",
    },
    {
        "name": "gt",
        "type": "int",
        "constraint": "DEFAULT -1",
        "category": "samples",
        "description": "Genotype",
    },
]


# ==================================================
#
#  SQL HELPER
#
# ===================================================


def get_sql_connection(filepath: str) -> sqlite3.Connection:
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

    # CUSTOM TYPE

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
    connection.create_function("current_user", 0, lambda: getpass.getuser())
    connection.create_aggregate("STD", 1, StdevFunc)

    if LOGGER.getEffectiveLevel() == logging.DEBUG:
        # Enable tracebacks from custom functions in DEBUG mode only
        sqlite3.enable_callback_tracebacks(True)

    # connection.set_trace_callback(lambda x: LOGGER.debug("[SQLITE]: " + x))

    return connection


def get_database_file_name(conn: sqlite3.Connection) -> str:
    """Return sqlite filename name

    Args:
        conn (sqlite3.Connection): Sqlite3 connection

    Returns:
        str: Path of the salite database
    """
    return conn.execute("PRAGMA database_list").fetchone()["file"]


def schema_exists(conn: sqlite3.Connection) -> bool:
    """Return if databases schema has been created

    Args:
        conn (sqlite3.Connection): Description

    Returns:
        bool
    """
    query = "SELECT count(*) FROM sqlite_master WHERE type = 'table'"
    return conn.execute(query).fetchone()[0] > 0


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


def drop_table(conn, table_name: str):
    """Drop the given table

    Args:
        conn (sqlite3.connection): Sqlite3 connection
        table_name (str): sqlite table name
    """
    cursor = conn.cursor()
    cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
    conn.commit()


def clear_table(conn: sqlite3.Connection, table_name: str):
    """Clear content of the given table

    Args:
        conn (sqlite3.Connection): Sqlite3 Connection
        table_name (str): sqlite table name
    """
    cursor = conn.cursor()
    cursor.execute(f"DELETE  FROM {table_name}")
    conn.commit()


def get_table_columns(conn: sqlite3.Connection, table_name: str):
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
    return [c[1] for c in conn.execute(f"pragma table_info({table_name})") if c[1] != "id"]


def alter_table(conn: sqlite3.Connection, table_name: str, fields: list):
    """Add new columns to a table

    Args:
        conn (sqlite3.Connection)
        table_name (str): sql table name
        fields (list): list of dict with name and type.
    """
    for field in fields:

        name = field["name"]
        p_type = field["type"]
        s_type = PYTHON_TO_SQLITE.get(p_type, "TEXT")
        constraint = field.get("constraint", "")
        sql = f"ALTER TABLE {table_name} ADD COLUMN `{name}` {s_type} {constraint}"

        try:
            conn.execute(sql)

        except sqlite3.OperationalError as e:
            LOGGER.error(e)

    conn.commit()


def alter_table_from_fields(conn: sqlite3.Connection, fields: list):
    """Alter tables from fields description

    Args:
        conn (sqlite3.Connection): sqlite databases
        fields (list): list if Fields {"name":"chr","type":"str","category":"variants"}
    """

    # Tables to alters
    tables = ["variants", "annotations", "genotypes"]

    # If shema exists, create database shema
    if not schema_exists(conn):
        LOGGER.error("CANNOT ALTER TABLE. NO SCHEMA AVAILABLE")
        return

    for table in tables:

        category = "samples" if table == "genotypes" else table

        # Get local columns names
        local_col_names = set(get_table_columns(conn, table))

        # get new fields which are not in local
        new_fields = [
            i for i in fields if i["category"] == category and i["name"] not in local_col_names
        ]

        if new_fields:
            alter_table(conn, table, new_fields)


def count_query(conn: sqlite3.Connection, query: str) -> int:
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
    pass
    # get_fields.cache_clear()
    # get_field_by_category.cache_clear()


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


def get_indexed_fields(conn: sqlite3.Connection) -> List[tuple]:
    """Returns, for this connection, a list of indexed fields
    Each element of the returned list is a tuple of (category,field_name)

    Args:
        conn (sqlite3.Connection): Sqlite3 connection

    Returns:
        List[tuple]: (category, field_name) of all the indexed fields
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
    indexed_variant_fields: list = None,
    indexed_annotation_fields: list = None,
    indexed_sample_fields: list = None,
    progress_callback: Callable = None,
):
    """Create extra indexes on tables

    Args:
        conn (sqlite3.Connection): Sqlite3 Connection

    Note:
        This function must be called after batch insertions.
        You should use this function instead of individual functions.

    """

    if progress_callback:
        progress_callback("Create selection index ")

    create_selections_indexes(conn)

    if progress_callback:
        progress_callback("Create variants index ")

    create_variants_indexes(conn, indexed_variant_fields)

    if progress_callback:
        progress_callback("Create samples index ")

    create_samples_indexes(conn, indexed_sample_fields)

    try:
        # Some databases have not annotations table
        if progress_callback:
            progress_callback("Create annotation index  ")
        create_annotations_indexes(conn, indexed_annotation_fields)

    except sqlite3.OperationalError as e:
        LOGGER.debug("create_indexes:: sqlite3.%s: %s", e.__class__.__name__, str(e))


def get_clean_fields(fields: Iterable[dict] = None) -> Iterable[dict]:
    """Helper function to add missing fields from MANDATORY FIELDS

    if Not fields specified, it will returns only mandatory fields

    Args:
        fields (Iterable[dict]): list of fields

    Yields:
        Iterable[dict]: list of fields
    """

    if fields is None:
        fields = []

    required_fields = {(f["category"], f["name"]): f for f in MANDATORY_FIELDS}
    input_fields = {(f["category"], f["name"]): f for f in fields}

    required_fields.update(input_fields)

    for field in required_fields.values():
        yield field


def get_accepted_fields(fields: Iterable[dict], ignored_fields: Iterable[dict]) -> Iterable[dict]:
    """Helper function to get fields without ignored fields

    Args:
        fields (Iterable[dict])
        ignored_fields (Iterable[dict])
    """

    ignored_keys = {(f["category"], f["name"]) for f in ignored_fields}
    return list(filter(lambda x: (x["category"], x["name"]) not in ignored_keys, fields))


def get_clean_variants(variants: Iterable[dict]) -> Iterable[dict]:
    """Helper function to get variant without missing fields

    Args:
        variants (Iterable[dict]): list of variant

    Yields:
        Iterable[dict]: list of variants
    """

    # Build default variant with mandatory keys
    # default_variant = {
    #     f["name"]: None for f in MANDATORY_FIELDS if f["category"] == "variants"
    # }

    for variant in variants:
        variant["is_indel"] = len(variant["ref"]) != len(variant["alt"])
        variant["is_snp"] = len(variant["ref"]) == len(variant["alt"])
        variant["annotation_count"] = len(variant["annotations"]) if "annotations" in variant else 0

        yield variant


# ==================================================
#
#  CRUD Operation
#
# ===================================================

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
        "INSERT OR REPLACE INTO projects (key, value) VALUES (?, ?)",
        list(project.items()),
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

    conn.execute("CREATE TABLE metadatas (key TEXT PRIMARY KEY, value TEXT)")


def update_metadatas(conn: sqlite3.Connection, metadatas: dict):
    """Populate metadatas with a key/value dictionnaries

    Args:
        conn (sqlite3.Connection): Sqlite3 Connection
        metadatas (dict, optional)
    """
    if metadatas:
        cursor = conn.cursor()
        cursor.executemany(
            "INSERT OR REPLACE INTO metadatas (key,value) VALUES (?,?)",
            list(metadatas.items()),
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


## History


def get_histories(conn: sqlite3.Connection, table: str, table_id: int) -> dict:
    """Return histories items

    Args:
        conn (sqlite3.Connection): Description
        table (str): table name (variants, samples, genotypes)
        table_id (int): record id

    Todo: test function
    """
    conn.row_factory = sqlite3.Row
    for rec in conn.execute(
        f"SELECT * FROM `history` WHERE `table`=? AND `table_rowid` = ? ", (table, table_id)
    ):
        yield (dict(rec))


## selections & sets tables ====================================================


def create_table_selections(conn: sqlite3.Connection):
    """Create the table "selections" and association table "selection_has_variant"

    This table stores variants selection saved by the user:

        - name: name of the set of variants
        - count: number of variants concerned by this set
        - query: the SQL query which generated the set
        - description: description of the selection

    Args:
        conn (sqlite3.Connection): Sqlite3 Connection
    """
    cursor = conn.cursor()
    # selection_id is an alias on internal autoincremented 'rowid'
    cursor.execute(
        """CREATE TABLE selections (
        id INTEGER PRIMARY KEY ASC,
        name TEXT UNIQUE, count INTEGER, query TEXT, description TEXT
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


def insert_selection(
    conn: sqlite3.Connection,
    query: str,
    name: str = "no_name",
    count: int = 0,
    description: str = None,
) -> int:
    """Insert one record in the selection table and return the last insert id.
    This function is used by `insert_selection_from_[source|bed|sql]` functions.

    Do not use this function. Use insert_selection_from_[source|bed|sql].

    Args:
        conn (sqlite3.Connection): Sqlite3 Connection.
        query (str): a VQL query
        name (str, optional): Name of the selection (default: "no_name")
        count (int, optional): Count of variant in the selection (default: 0)
        description (str, optional): Description of the selection (default: None)

    Returns:
        int: Return last rowid

    See Also:
        create_selection_from_sql()
        create_selection_from_source()
        create_selection_from_bed()

    Warning:
        This function does a commit !


    """

    if name == DEFAULT_SELECTION_NAME and description is None:
        description = "All variants"

    cursor = conn.cursor()

    cursor.execute(
        "INSERT OR REPLACE INTO selections (name, count, query, description) VALUES (?,?,?,?)",
        (name, count, query, description),
    )

    conn.commit()

    return cursor.lastrowid


def insert_selection_from_source(
    conn: sqlite3.Connection,
    name: str,
    source: str = DEFAULT_SELECTION_NAME,
    filters=None,
    count: int = None,
    description: str = None,
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
        description (str/None, optional): Description of the source

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
    selection_id = insert_selection(
        conn=conn, query=vql_query, name=name, count=count, description=description
    )

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
    # times with an association? ==> YES it is

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


def insert_selection_from_samples(
    conn: sqlite3.Connection,
    samples: list,
    name: str = SAMPLES_SELECTION_NAME,
    gt_min: int = 0,
    force: bool = True,
    description: str = None,
) -> int:
    """Create a selection from samples.
    This function create a subselection from a list of samples.

    Examples:

    Create a subselection from samples ["sample1", "sample2"].

        insert_selection_from_samples(
            conn,
            samples = ["sample1", "sample2"],
            name = "samples",
            gt_min = 0,
            force = True,
            description = None
        )

    Args:
        conn (sqlite3.connection): Sqlite3 connection
        samples (list): List of sample names
        name (str/<SAMPLES_SELECTION_NAME>, optional): Name of selection (constant variable by default)
        gt_min (int/0, optional): a filters to create selection
        force (bool/True, optional): Force insertion of selection if exists
        description (str/None, optional): Description of the source

    Returns:
        selection_id, if lines have been inserted; None if selection exists and not force; None otherwise (rollback).
    """

    samples_clause = "(" + ",".join([f"'{i}'" for i in samples]) + ")"
    ids = ",".join(
        [
            str(dict(rec)["id"])
            for rec in conn.execute(f"SELECT id FROM samples WHERE name in {samples_clause}")
        ]
    )

    query = f"""SELECT distinct(id) FROM variants INNER JOIN genotypes ON genotypes.variant_id = variants.id 
    WHERE genotypes.sample_id IN ({ids}) AND genotypes.gt > {gt_min}"""

    # Construct description automatically from samples
    if description == None and (
        name == SAMPLES_SELECTION_NAME or name == CURRENT_SAMPLE_SELECTION_NAME
    ):
        description = ",".join(samples)

    # check if same query
    selections = get_selections(conn)
    query_in_db = None
    for s in selections:
        if s["name"] == name:
            query_in_db = s["query"]

    # Create/modify selection
    if query_in_db != query or force:
        LOGGER.debug(f"""Source '{name}' created/updated""")
        return insert_selection_from_sql(conn=conn, query=query, name=name, description=description)
    else:
        LOGGER.debug(f"""Source '{name}' already in DB""")
        return None


def insert_selection_from_sql(
    conn: sqlite3.Connection,
    query: str,
    name: str,
    count: int = None,
    from_selection: bool = False,
    description: str = None,
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
        description (str/"", optional): Description of the source

    Returns:
        selection_id, if lines have been inserted; None otherwise (rollback).
    """
    cursor = conn.cursor()

    # Compute query count
    # TODO : this can take a while .... need to compute only one from elsewhere
    if count is None:
        count = count_query(conn=conn, query=query)

    # Create selection
    selection_id = insert_selection(
        conn=conn, query=query, name=name, count=count, description=description
    )

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
    conn: sqlite3.Connection, source: str, target: str, bed_intervals, description: str = None
) -> int:
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

    # generate description
    if not description:
        description = "from BED file"

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

    return insert_selection_from_sql(
        conn=conn, query=query, name=target, from_selection=True, description=description
    )


def get_selections(conn: sqlite3.Connection) -> List[dict]:
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
    conn.execute("UPDATE selections SET name=:name, count=:count WHERE id = :id", selection)
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
        + " INTERSECT ".join([f"SELECT value FROM wordsets WHERE name = '{w}'" for w in wordsets])
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
        + " UNION ".join([f"SELECT value FROM wordsets WHERE name = '{w}'" for w in wordsets])
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
        + " EXCEPT ".join([f"SELECT value FROM wordsets WHERE name = '{w}'" for w in wordsets])
        + ")"
    )
    cursor = conn.cursor()
    cursor.execute(query)
    conn.commit()
    return cursor.rowcount


def get_wordsets(conn: sqlite3.Connection):
    """Return the number of words per word set stored in DB

    Returns:
        generator[dict]: Yield dictionaries with `name` and `count` keys.
    """
    for row in conn.execute("SELECT name, COUNT(*) as 'count' FROM wordsets GROUP BY name"):
        yield dict(row)


def get_wordset_by_name(conn, wordset_name):
    """Return generator of words in the given word set

    Returns:
        generator[str]: Yield words of the word set.
    """
    for row in conn.execute("SELECT DISTINCT value FROM wordsets WHERE name = ?", (wordset_name,)):
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
    Fields are the columns of the tables: variants, annotations and genotypes.
    Fields are extracted from reader objects and are dynamically constructed.

    variants:
    Chr,pos,ref,alt, filter, qual, dp, af, etc.

    annotations:
    Gene, transcrit, etc.

    genotypes:
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


def insert_field(conn, name="no_name", category="variants", field_type="text", description=""):
    """Insert one fields

    This is a shortcut and it calls insert_fields with one element

    Args:
        conn (sqlite.Connection): sqlite Connection
        name (str, optional): fields name. Defaults to "no_name".
        category (str, optional): fields table. Defaults to "variants".
        field_type (str, optional): type of field in python (str,int,float,bool). Defaults to "text".
        description (str, optional): field description"""

    insert_fields(
        conn,
        [
            {
                "name": name,
                "category": category,
                "type": field_type,
                "description": description,
            }
        ],
    )


def insert_fields(conn: sqlite3.Connection, data: list):
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
        INSERT OR IGNORE INTO fields (name,category,type,description)
        VALUES (:name,:category,:type,:description)
        """,
        data,
    )
    conn.commit()


# def insert_only_new_fields(conn, data: list):
#     """Insert in "fields" table the fields who did not already exist.
#     Add those fields as new columns in "variants", "annotations" or "samples" tables.

#     :param conn: sqlite3.connect
#     :param data: list of field dictionnary
#     """
#     get_fields.cache_clear()
#     existing_fields = [(f["name"], f["category"]) for f in get_fields(conn)]
#     new_data = [f for f in data if (f["name"], f["category"]) not in existing_fields]
#     cursor = conn.cursor()
#     cursor.executemany(
#         """
#         INSERT INTO fields (name,category,type,description)
#         VALUES (:name,:category,:type,:description)
#         """,
#         new_data,
#     )
#     for field in new_data:
#         cursor.execute(
#             "ALTER TABLE %s ADD COLUMN %s %s"
#             % (field["category"], field["name"], field["type"])
#         )
#     conn.commit()

# @lru_cache()
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


# @lru_cache()
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
    """Return field by its nam

    .. seealso:: get_fields

    :param conn: sqlite3.connect
    :param field_name: field name
    :return: field record or None if not found.
    :rtype: <dict> or None
    """
    conn.row_factory = sqlite3.Row
    field_data = conn.execute("SELECT * FROM fields WHERE name = ? ", (field_name,)).fetchone()
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
        FROM genotypes
        JOIN samples ON genotypes.sample_id = samples.id
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
        query = f""" SELECT DISTINCT `{field_name}` FROM genotypes """

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


def create_table_annotations(conn: sqlite3.Connection, fields: List[dict]):
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
        LOGGER.debug("create_table_annotations:: No annotation fields detected! => Fallback")
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
    conn.execute("CREATE INDEX IF NOT EXISTS `idx_annotations` ON annotations (`variant_id`)")

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
    for annotation in conn.execute(f"SELECT * FROM annotations WHERE variant_id = {variant_id}"):
        yield dict(annotation)


## variants table ==============================================================


def create_table_variants(conn: sqlite3.Connection, fields: List[dict]):
    """Create "variants" and "genotypes" tables which contains dynamics fields

    :Example:

        fields = get_fields()
        create_table_variants(conn, fields)

    .. seealso:: get_fields

    .. note:: "gt" field in "genotypes" = Patient's genotype.
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
            f'`{field["name"]}` {PYTHON_TO_SQLITE.get(field["type"],"TEXT")} {field.get("constraint", "")}'
            for field in fields
            if field["name"]
        ]
    )

    # print("ICI", schema)

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
        "CREATE INDEX IF NOT EXISTS `idx_genotypes` ON genotypes (`variant_id`, `sample_id`)"
    )

    # Complementary index on sample_id
    conn.execute("CREATE INDEX IF NOT EXISTS `idx_genotypes_sample_id` ON genotypes (`sample_id`)")

    # Complementary index on variant_id
    conn.execute(
        "CREATE INDEX IF NOT EXISTS `idx_genotypes_variant_id` ON genotypes (`variant_id`)"
    )

    # Complementary index on gt
    conn.execute("CREATE INDEX IF NOT EXISTS `idx_genotypes_gt` ON genotypes (`gt`)")

    # Complementary index oon classification
    conn.execute(
        "CREATE INDEX IF NOT EXISTS `idx_genotypes_classification` ON genotypes (`classification`)"
    )

    for field in indexed_fields:
        conn.execute(f"CREATE INDEX IF NOT EXISTS `idx_variants_{field}` ON variants (`{field}`)")


def get_variant(
    conn: sqlite3.Connection, variant_id: int, with_annotations=False, with_samples=False
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
            \+ all fields of genotypes associated to all samples if
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
        conn.execute(f"SELECT * FROM variants WHERE variants.id = {variant_id}").fetchone()
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
                f"""SELECT samples.name, genotypes.* FROM samples
                LEFT JOIN genotypes on samples.id = genotypes.sample_id
                WHERE variant_id = {variant_id} """
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
    query = "UPDATE variants SET " + ",".join(placeholders) + f" WHERE id = {variant['id']}"
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


def get_variant_occurences(conn: sqlite3.Connection, variant_id: int):
    """Return variant statistics

    Args:
        conn (sqlite3.Connection)
        variant_id (int): variant id
    """

    for rec in conn.execute(
        f"""
        SELECT samples.name, genotypes.* FROM genotypes 
        INNER JOIN samples ON samples.id = genotypes.sample_id 
        WHERE genotypes.variant_id = {variant_id} AND genotypes.gt > 0"""
    ):
        yield dict(rec)


def get_variant_occurences_summary(conn: sqlite3.Connection, variant_id: int):

    for rec in conn.execute(
        f"""
        SELECT gt , COUNT(*) as count FROM genotypes 
        WHERE variant_id = {variant_id} GROUP BY gt """
    ):
        yield dict(rec)


def get_summary(conn: sqlite3.Connection):
    """Get summary of database

    Args:
        conn (sqlite3.Connection)
    """
    variant_count = int(
        conn.execute("SELECT count FROM selections WHERE name = 'variants'").fetchone()
    )
    sample_count = int(conn.execute("SELECT COUNT(*) FROM samples").fetchone())

    return {"variant_count": variant_count, "sample_count": sample_count}


def get_sample_variant_classification_count(
    conn: sqlite3.Connection, sample_id: int, classification: int
):
    """
    Used for edit boxes
    Returns total of variants having a given classification (validation status) for a given sample
    """
    # r = conn.execute(f"SELECT COUNT(*) FROM variants v LEFT JOIN genotypes sv WHERE sv.sample_id={sample_id} AND sv.variant_id = v.id AND v.classification = {classification}").fetchone()[0]
    r = conn.execute(
        f"SELECT COUNT(*) FROM genotypes sv WHERE sv.sample_id={sample_id} AND classification = {classification}"
    ).fetchone()[0]
    return int(r)


def get_sample_variant_classification(
    conn: sqlite3.Connection, sample_id: int = None, variant_id: int = None
):
    """
    Used for edit boxes
    Returns genotypes for a given sample or a given variant
    """
    where_clause = " 1=1 "
    if sample_id:
        where_clause += f" AND genotypes.sample_id={sample_id} "
    if variant_id:
        where_clause += f" AND genotypes.variant_id={variant_id} "
    r = conn.execute(
        f"""
        SELECT samples.name, genotypes.* 
        FROM genotypes
        INNER JOIN samples ON samples.id = genotypes.sample_id 
        WHERE {where_clause}
        """
    )
    return (dict(data) for data in r)


def get_samples_from_query(conn: sqlite3.Connection, query: str):
    """Selects all the samples matching query
    Example query:
    "classification:3,4 sex:1 phenotype:3"
    Will call:
    "SELECT * FROM samples WHERE classification in (3,4) AND sex=1 AND phenotype=3"

    Args:
        conn (sqlite3.Connection)
        query (str): the query string
    """

    if not query:
        return get_samples(conn)

    or_list = []
    for word in query.split():
        if ":" not in word:
            word = f"name:{word}"
        for i in re.findall(r"(.+):(.+)", word):
            if "," in i[1]:
                key, val = i[0], f"{i[1]}"
                val = ",".join([f"'{i}'" for i in val.split(",")])
                or_list.append(f"{key} IN ({val})")
            else:
                key, val = i[0], i[1]
                if key in ("name", "tags"):
                    or_list.append(f"{key} LIKE '%{val}%'")
                else:
                    or_list.append(f"{key} = '{val}'")

    sql_query = f"SELECT * FROM samples WHERE {' OR '.join(or_list)}"
    # Suppose conn.row_factory = sqlite3.Row

    return (dict(data) for data in conn.execute(sql_query))


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


def update_variants_counts(
    conn: sqlite3.Connection,
    progress_callback: Callable = None,
):
    """Update all variants counts information from sample data.

    It computes count_var,count_hom, count_het, count_ref for each variants by reading how many samples belong to.
    This methods can takes a while and should be run everytime new samples are added.

    Args:
        conn (sqlite3.Connection)
    """

    # Update count_het
    if progress_callback:
        progress_callback("Variants count_het")
    conn.execute(
        """
        UPDATE variants
        SET count_het = geno.count
        FROM (SELECT variant_id, count(sample_id) as count
            FROM genotypes
            WHERE genotypes.gt = 1
            GROUP BY variant_id) as geno
        WHERE id = geno.variant_id;
        """
    )

    # Update count_hom
    if progress_callback:
        progress_callback("Variants count_hom")
    conn.execute(
        """
        UPDATE variants
        SET count_hom = geno.count
        FROM (SELECT variant_id, count(sample_id) as count
            FROM genotypes
            WHERE genotypes.gt = 2
            GROUP BY variant_id) as geno
        WHERE id = geno.variant_id;
        """
    )

    # Update count_ref
    if progress_callback:
        progress_callback("Variants count_ref")
    conn.execute(
        """
        UPDATE variants
        SET count_ref = geno.count
        FROM (SELECT variant_id, count(sample_id) as count
            FROM genotypes
            WHERE genotypes.gt = 0
            GROUP BY variant_id) as geno
        WHERE id = geno.variant_id;
        """
    )

    # Update count_var
    if progress_callback:
        progress_callback("Variants count_var")
    conn.execute(
        """
        UPDATE variants
        SET count_var = count_het + count_hom
        """
    )

    # sample_count
    sample_count = conn.execute("SELECT COUNT(id) FROM samples").fetchone()[0]

    # Update count_tot
    if progress_callback:
        progress_callback("Variants count_tot")
    conn.execute(
        f"""
        UPDATE variants
        SET count_tot = {sample_count}
        """
    )

    # Update count_none
    if progress_callback:
        progress_callback("Variants count_none")
    conn.execute(
        f"""
        UPDATE variants
        SET count_none = count_tot - count_var
        """
    )

    # Update freq_var
    if progress_callback:
        progress_callback("Variants freq_var")
    conn.execute(
        """
        UPDATE variants
        SET freq_var = ( cast ( ( (count_hom * 2) + count_het ) as real) / ( cast ( (count_tot * 2) as real ) ) )
        """
    )

    conn.commit()

    # CASE and CONTROL

    # If no phenotype, do not compute any thing...
    pheno_count = conn.execute(
        "SELECT COUNT(phenotype) FROM samples WHERE phenotype > 0"
    ).fetchone()[0]
    if pheno_count == 0:
        LOGGER.warning("No phenotype. Do not compute case/control count")
        return

    # case hom
    conn.execute(
        """
        UPDATE variants
        SET case_count_hom = geno.count
        FROM (SELECT variant_id, count(sample_id) as count
            FROM genotypes, samples
            WHERE genotypes.sample_id=samples.id AND genotypes.gt = 2 AND samples.phenotype=2
            GROUP BY variant_id) as geno
        WHERE id = geno.variant_id;
        """
    )

    # case het
    conn.execute(
        """
        UPDATE variants
        SET case_count_het = geno.count
        FROM (SELECT variant_id, count(sample_id) as count
            FROM genotypes, samples
            WHERE genotypes.sample_id=samples.id AND genotypes.gt = 1 AND samples.phenotype=2
            GROUP BY variant_id) as geno
        WHERE id = geno.variant_id;
        """
    )

    # case ref
    conn.execute(
        """
        UPDATE variants
        SET case_count_ref = geno.count
        FROM (SELECT variant_id, count(sample_id) as count
            FROM genotypes, samples
            WHERE genotypes.sample_id=samples.id AND genotypes.gt = 0 AND samples.phenotype=2
            GROUP BY variant_id) as geno
        WHERE id = geno.variant_id;
        """
    )

    # control hom
    conn.execute(
        """
        UPDATE variants
        SET control_count_hom = geno.count
        FROM (SELECT variant_id, count(sample_id) as count
            FROM genotypes, samples
            WHERE genotypes.sample_id=samples.id AND genotypes.gt = 2 AND samples.phenotype=1
            GROUP BY variant_id) as geno
        WHERE id = geno.variant_id;
        """
    )

    # control het
    conn.execute(
        """
        UPDATE variants
        SET control_count_het = geno.count
        FROM (SELECT variant_id, count(sample_id) as count
            FROM genotypes, samples
            WHERE genotypes.sample_id=samples.id AND genotypes.gt = 1 AND samples.phenotype=1
            GROUP BY variant_id) as geno
        WHERE id = geno.variant_id;
        """
    )

    # control ref
    conn.execute(
        """
        UPDATE variants
        SET control_count_ref = geno.count
        FROM (SELECT variant_id, count(sample_id) as count
            FROM genotypes, samples
            WHERE genotypes.sample_id=samples.id AND genotypes.gt = 0 AND samples.phenotype=1
            GROUP BY variant_id) as geno
        WHERE id = geno.variant_id;
        """
    )

    conn.commit()


def insert_variants(
    conn: sqlite3.Connection,
    variants: List[dict],
    total_variant_count: int = None,
    progress_every: int = 1000,
    progress_callback: Callable = None,
):
    """Insert many variants from data into variants table

    Args:
        conn (sqlite3.Connection): sqlite3 Connection
        data (list): list of variant dictionnary which contains same number of key than fields numbers.
        total_variant_count (None, optional): total variant count, to compute progression
        yield_every (int, optional): Yield a tuple with progression and message.
        Progression is 0 if total_variant_count is not set.


    Example:

        insert_many_variant(conn, [{chr:"chr1", pos:24234, alt:"A","ref":T }])
        insert_many_variant(conn, reader.get_variants())

    Note: About using INSERT OR IGNORE: They avoid the following errors:

        - Upon insertion of a duplicate key where the column must contain
          a PRIMARY KEY or UNIQUE constraint
        - Upon insertion of NULL value where the column has
          a NOT NULL constraint.
          => This is not recommended


    """

    variants_local_fields = set(get_table_columns(conn, "variants"))
    annotations_local_fields = set(get_table_columns(conn, "annotations"))
    samples_local_fields = set(get_table_columns(conn, "genotypes"))

    # get samples name / samples id map
    samples_map = {sample["name"]: sample["id"] for sample in get_samples(conn)}

    progress = -1
    errors = 0
    cursor = conn.cursor()
    batches = []
    total = 0

    RETURNING_ENABLE = parse_version(sqlite3.sqlite_version) >= parse_version("3.35.0 ")

    for variant_count, variant in enumerate(variants):

        variant_fields = {i for i in variant.keys() if i not in ("samples", "annotations")}

        common_fields = variant_fields & variants_local_fields

        query_fields = ",".join((f"`{i}`" for i in common_fields))
        query_values = ",".join((f"?" for i in common_fields))
        query_datas = [variant[i] for i in common_fields]

        # INSERT VARIANTS

        if RETURNING_ENABLE:
            query = f"""INSERT INTO variants ({query_fields}) VALUES ({query_values}) ON CONFLICT (chr,pos,ref,alt) 
            DO UPDATE SET ({query_fields}) = ({query_values}) RETURNING id
            """
            res = cursor.execute(query, query_datas * 2).fetchone()
            variant_id = dict(res)["id"]
        else:
            query = f"""INSERT INTO variants ({query_fields}) VALUES ({query_values}) ON CONFLICT (chr,pos,ref,alt) 
            DO UPDATE SET ({query_fields}) = ({query_values})
            """
            # Use execute many and get last rowS inserted ?
            cursor.execute(query, query_datas * 2)

            chrom = variant["chr"]
            pos = variant["pos"]
            ref = variant["ref"]
            alt = variant["alt"]

            variant_id = conn.execute(
                f"SELECT id FROM variants where chr='{chrom}' AND pos = {pos} AND ref='{ref}' AND alt='{alt}'"
            ).fetchone()[0]

        total += 1

        # variant_id = conn.execute(
        #     f"SELECT id FROM variants where chr='{chrom}' AND pos = {pos} AND ref='{ref}' AND alt='{alt}'"
        # ).fetchone()[0]

        # variant_id = cursor.lastrowid

        if variant_id == 0:
            LOGGER.debug(
                """ The following variant contains erroneous data; most of the time it is a 
                duplication of the primary key: (chr,pos,ref,alt).
                Please check your data; this variant and its attached data will not be inserted!\n%s"""
            )
            errors += 1
            total -= 1
            continue

        # INSERT ANNOTATIONS
        if "annotations" in variant:
            # Delete previous annotations
            cursor.execute(f"DELETE FROM annotations WHERE variant_id ={variant_id}")
            for ann in variant["annotations"]:

                ann["variant_id"] = variant_id
                common_fields = annotations_local_fields & ann.keys()
                query_fields = ",".join((f"`{i}`" for i in common_fields))
                query_values = ",".join((f"?" for i in common_fields))
                query_datas = [ann[i] for i in common_fields]
                query = (
                    f"INSERT OR REPLACE INTO annotations ({query_fields}) VALUES ({query_values})"
                )

                cursor.execute(query, query_datas)

        # INSERT SAMPLES

        if "samples" in variant:
            for sample in variant["samples"]:
                if sample["name"] in samples_map:

                    sample["variant_id"] = int(variant_id)
                    sample["sample_id"] = int(samples_map[sample["name"]])

                    sample["gt"] = sample.get("gt", -1)
                    if sample["gt"] < 0:  # Allow genotype 1,2,3,4,5,... ( for other species )
                        # remove gt if exists
                        query_remove = f"""DELETE FROM genotypes WHERE variant_id={sample["variant_id"]} AND sample_id={sample["sample_id"]}"""
                        cursor.execute(query_remove)
                    else:
                        common_fields = samples_local_fields & sample.keys()
                        query_fields = ",".join((f"`{i}`" for i in common_fields))
                        query_values = ",".join((f"?" for i in common_fields))
                        query_datas = [sample[i] for i in common_fields]
                        query = f"""INSERT INTO genotypes ({query_fields}) VALUES ({query_values}) ON CONFLICT (variant_id, sample_id)
                        DO UPDATE SET ({query_fields}) = ({query_values})
                        """
                        cursor.execute(query, query_datas * 2)

        # Commit every batch_size
        if progress_callback and variant_count != 0 and variant_count % progress_every == 0:
            progress_callback(f"{variant_count} variants inserted.")

    conn.commit()

    if progress_callback:
        progress_callback(f"{total} variant(s) has been inserted with {errors} error(s)")

    # Create default selection (we need the number of variants for this)

    # Count total variants . I cannot use "total" variable like before for the update features.

    true_total = conn.execute("SELECT COUNT(*) FROM variants").fetchone()[0]
    insert_selection(conn, query="", name=DEFAULT_SELECTION_NAME, count=true_total)


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


def get_variant_groupby_for_samples(conn: sqlite3.Connection, groupby: str, samples: List[int], order_by=True) -> typing.Tuple[dict]:
    """Get count of variants for any field in "variants" or "genotype", 
    limited to samples in list

    Args:
        conn (sqlite3.Connection): db conn
        groupby (str): Field defining the GROUP BY
        samples (List[int]): list of sample ids on which the search is applied
        order_by (bool, optional): If True, results are ordered by the groupby field. Defaults to True.
    
    Return:
        tuple of dict ; each containing one group and its count
    """

    samples = ",".join([str(s) for s in samples])

    query = f"""SELECT {groupby}, COUNT(variants.id) as count 
    FROM variants
    INNER JOIN genotypes ON variants.id = genotypes.variant_id
    WHERE genotypes.sample_id IN ({samples})
    GROUP BY {groupby}
    """

    if order_by:
        query += f"ORDER BY {groupby}"

    conn.row_factory = sqlite3.Row
    return (dict(data) for data in conn.execute(query))



## History table ==================================================================
def create_table_history(conn):
    # TODO : rename to table_id
    conn.execute(
        """CREATE TABLE IF NOT EXISTS `history` (
        `id` INTEGER PRIMARY KEY ASC AUTOINCREMENT,
        `timestamp` TEXT DEFAULT (DATETIME('now')),
        `user` TEXT DEFAULT 'unknown',
        `table` TEXT DEFAULT '' NOT NULL,
        `table_rowid` INTEGER NOT NULL, 
        `field` TEXT DEFAULT '',
        `before` TEXT DEFAULT '',
        `after` TEXT DEFAULT '',
        UNIQUE (id)
        );"""
    )
    conn.commit()


def create_history_indexes(conn):
    """Create indexes on the "history" table"""
    conn.execute(f"CREATE INDEX IF NOT EXISTS `idx_history_user` ON history (`user`)")
    conn.execute(f"CREATE INDEX IF NOT EXISTS `idx_history_table` ON history (`table`)")
    conn.execute(f"CREATE INDEX IF NOT EXISTS `idx_history_table_rowid` ON history (`table_rowid`)")
    conn.execute(f"CREATE INDEX IF NOT EXISTS `idx_history_field` ON history (`field`)")


## Tags table ==================================================================
def create_table_tags(conn):

    conn.execute(
        """CREATE TABLE IF NOT EXISTS tags (
        id INTEGER PRIMARY KEY ASC,
        name TEXT,
        category TEXT DEFAULT 'variants',
        description TEXT,
        color TEXT DEFAULT 'red',
        UNIQUE (name, category)

        )"""
    )
    conn.commit()


def insert_tag(
    conn: sqlite3.Connection, name: str, category: str, description: str, color: str
) -> int:
    """Insert new tags and return id

    Args:
        conn (sqlite3.Connection)
        name (str): tags name
        category (str): variants or samples
        description (str): a description
        color (str): color in hexadecimal or color name
    """
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO tags (name, category, description, color) VALUES (?,?,?,?)",
        [name, category, description, color],
    )

    conn.commit()
    return cursor.lastrowid


def get_tags_from_samples(conn: sqlite3.Connection, separator="&") -> typing.List[str]:
    """TODO : pas optimal pou le moment"""
    tags = set()
    for record in conn.execute("SELECT tags FROM samples "):

        tags = tags.union({t for t in record["tags"].split(separator) if t})

    return tags


def get_tags(conn: sqlite3.Connection) -> List[dict]:
    """Return all tags

    Args:
        conn (sqlite3.Connection)

    Returns:
        List[dict]: List of tags
    """

    return [dict(item) for item in conn.execute("SELECT * FROM tags")]


def get_tag(conn: sqlite3.Connection, tag_id: int) -> dict:
    """Return tag id

    Args:
        conn (sqlite3.Connection):
        tag_id (int): Sql table id

    Returns:
        dict: Description
    """
    return conn.execute(f"SELECT * FROM tags WHERE id = {tag_id}").fetchone()


def update_tag(conn: sqlite3.Connection, tag: dict):

    if "id" not in tag:
        raise KeyError("'id' key is not in the given tag <%s>" % tag)

    unzip = lambda l: list(zip(*l))

    placeholders, values = unzip(
        [(f"`{key}` = ? ", value) for key, value in tag.items() if key != "id"]
    )
    query = "UPDATE tags SET " + ",".join(placeholders) + f" WHERE id = {tag['id']}"

    conn.execute(query, values)
    conn.commit()


def remove_tag(conn: sqlite3.Connection, tag_id: int):
    conn.execute(f"DELETE FROM tags WHERE id = {tag_id}")
    conn.commit()


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
        classification INTEGER DEFAULT 0,
        tags TEXT DEFAULT '',
        comment TEXT DEFAULT '',
        count_validation_positive_variant INTEGER DEFAULT 0,
        count_validation_negative_variant INTEGER DEFAULT 0,
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

    cursor.execute(
        f"""CREATE TABLE genotypes  (
        sample_id INTEGER NOT NULL,
        variant_id INTEGER NOT NULL,
        {schema},
        PRIMARY KEY (sample_id, variant_id),
        FOREIGN KEY (sample_id) REFERENCES samples (id)
          ON DELETE CASCADE
          ON UPDATE NO ACTION
        ) 
       """
    )

    # WITHOUT ROWID

    conn.commit()


def create_samples_indexes(conn, indexed_samples_fields=None):
    """Create indexes on the "samples" table"""
    if indexed_samples_fields is None:
        return

    for field in indexed_samples_fields:
        conn.execute(f"CREATE INDEX IF NOT EXISTS `idx_samples_{field}` ON genotypes (`{field}`)")


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


def insert_samples(conn, samples: list, import_id: str = None, import_vcf: str = None):
    """Insert many samples at a time in samples table.
    Set genotype to -1 in genotypes for all pre-existing variants.

    :param samples: List of samples names
    :param import_id: importID tag for each samples
    """

    current_date = datetime.today().strftime("%Y%m%d-%H%M%S")

    # import VCF
    import_vcf_tag = None
    if import_vcf:
        import_vcf_tag = "importVCF#" + import_vcf

    # import DATE
    import_date_tag = None
    import_date_tag = "importDATE#" + current_date

    # import ID
    import_id_tag = None
    if not import_id:
        import_id = current_date
    import_id_tag = "importID#" + import_id

    # cursor
    cursor = conn.cursor()

    for sample in samples:
        # insert Sample
        cursor.execute(f"INSERT OR IGNORE INTO samples (name) VALUES ('{sample}') ")
        # insert tags
        if import_vcf_tag:
            cursor.execute(
                f"UPDATE samples SET tags = '{import_vcf_tag}' WHERE name = '{sample}' AND tags = '' "
            )
            cursor.execute(
                f"UPDATE samples SET tags = tags || ',' || '{import_vcf_tag}' WHERE name = '{sample}' AND tags != '' AND ',' || tags || ',' NOT LIKE '%,{import_vcf_tag},%' "
            )
        if import_date_tag:
            cursor.execute(
                f"UPDATE samples SET tags = '{import_date_tag}' WHERE name = '{sample}' AND tags = '' "
            )
            cursor.execute(
                f"UPDATE samples SET tags = tags || ',' || '{import_date_tag}' WHERE name = '{sample}' AND tags != '' AND ',' || tags || ',' NOT LIKE '%,{import_date_tag},%' "
            )
        if import_id_tag:
            cursor.execute(
                f"UPDATE samples SET tags = '{import_id_tag}' WHERE name = '{sample}' AND tags = '' "
            )
            cursor.execute(
                f"UPDATE samples SET tags = tags || ',' || '{import_id_tag}' WHERE name = '{sample}' AND tags != '' AND ',' || tags || ',' NOT LIKE '%,{import_id_tag},%' "
            )

    # commit
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


def search_samples(conn: sqlite3.Connection, name: str, families=[], tags=[], classifications=[]):

    query = """
    SELECT * FROM samples
    """

    clauses = []

    if name:
        clauses.append(f"name LIKE '%{name}%'")

    if families:
        families_clause = ",".join(f"'{i}'" for i in families)
        clauses.append(f"family_id IN ({families_clause})")

    if classifications:
        classification_clause = ",".join(f"{i}" for i in classifications)
        clauses.append(f" classification IN ({classification_clause})")

    # if tags:
    #     tag_clause = ",".join(f"'{i}'" for i in tags)
    #     clauses.append(f" tags IN ({tag_clause})")

    if clauses:
        query += " WHERE " + " AND ".join(clauses)

    print(query)
    for sample in conn.execute(query):
        yield dict(sample)


def get_samples_family(conn: sqlite3.Connection):

    return {data["family_id"] for data in conn.execute("SELECT DISTINCT family_id FROM samples")}


def get_samples_by_family(conn: sqlite3.Connection, families=[]):

    placeholder = ",".join((f"'{i}'" for i in families))
    return (
        dict(data)
        for data in conn.execute(f"SELECT * FROM samples WHERE family_id IN ({placeholder})")
    )


def get_sample(conn: sqlite3.Connection, sample_id: int):
    """Get samples information from a specific id

    Args:
        conn (sqlite3.Connection): sqlite3.Connextion
        sample_id (int): sample table id
    """

    return dict(conn.execute(f"SELECT * FROM samples WHERE id = {sample_id}").fetchone())


def get_sample_annotations(conn, variant_id: int, sample_id: int):
    """Get samples for given sample id and variant id"""
    conn.row_factory = sqlite3.Row
    return dict(
        conn.execute(
            f"SELECT * FROM genotypes WHERE variant_id = {variant_id} and sample_id = {sample_id}"
        ).fetchone()
    )


def get_sample_nb_genotype_by_classification(conn, sample_id: int):
    """Get number of genotype by classification for given sample id"""
    conn.row_factory = sqlite3.Row
    return dict(
        conn.execute(
            f"SELECT genotypes.classification as classification, count(genotypes.variant_id) as nb_genotype FROM genotypes WHERE genotypes.sample_id = '{sample_id}' GROUP BY genotypes.classification"
        )
    )


def get_if_sample_has_classified_genotypes(conn, sample_id: int):
    """Get if sample id has classificed genotype (>0)"""
    conn.row_factory = sqlite3.Row
    res = conn.execute(
        f"SELECT 1 as variant FROM genotypes WHERE genotypes.sample_id = '{sample_id}' AND classification > 0 LIMIT 1"
    ).fetchone()
    if res:
        return True
    else:
        return False


def get_genotypes(conn, variant_id: int, fields: List[str] = None, samples: List[str] = None):
    """Get samples annotation for a specific variant using different filters

    This function is used by the sample plugins.

    Args:
        conn (TYPE)
        variant_id (int): variant id
        fields (List[str], optional): Fields list from genotypes table
        samples (List[str], optional): Samples filters
        family (List[str], optional): Family filters
        tags (List[str], optional): Tags filters
        genotype (List[str], optional): genotype filters
    """
    fields = fields or ["gt"]

    sql_fields = ",".join([f"sv.{f}" for f in fields])

    query = f"""SELECT sv.sample_id, sv.variant_id, samples.name , {sql_fields} FROM samples
    LEFT JOIN genotypes sv 
    ON sv.sample_id = samples.id AND sv.variant_id = {variant_id}  """

    conditions = []

    if samples:
        sample_clause = ",".join([f"'{s}'" for s in samples])
        query += f"WHERE samples.name IN ({sample_clause})"

    return (dict(data) for data in conn.execute(query))


def get_genotype_rowid(conn: sqlite3.Connection, variant_id: int, sample_id: int):
    """
    Used to determine rowid to fill the "history" table

    Args:
        sample_id (int): sql sample id
        variant_id (int): sql variant id

    Returns:
        rowid (int): rowid from "genotypes" table corresponding to sample_id and variant_id
    """
    conn.row_factory = sqlite3.Row
    return dict(
        conn.execute(
            f"SELECT genotypes.rowid FROM genotypes WHERE variant_id = {variant_id} AND sample_id = {sample_id}"
        ).fetchone()
    )["rowid"]


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

    query = "UPDATE samples SET " + ",".join(sql_set) + " WHERE id = " + str(sample["id"])
    conn.execute(query, sql_val)
    conn.commit()


def update_genotypes(conn: sqlite3.Connection, data: dict):
    """Summary

    data must contains variant_id and sample_id

    Args:
        conn (sqlite3.Connection): Description
        data (dict): Data to update

    """
    if "variant_id" not in data and "sample_id" not in data:
        logging.debug("id is required")
        return

    sql_set = []
    sql_val = []

    for key, value in data.items():
        if key not in ("variant_id", "sample_id"):
            sql_set.append(f"`{key}` = ? ")
            sql_val.append(value)

    sample_id = data["sample_id"]
    variant_id = data["variant_id"]
    query = (
        "UPDATE genotypes SET "
        + ",".join(sql_set)
        + f" WHERE sample_id = {sample_id} AND variant_id = {variant_id}"
    )

    # print("ICCCCCCCCCCCCCCCCC", query)
    conn.execute(query, sql_val)
    conn.commit()


# ==================== CREATE DATABASE =====================================


def create_triggers(conn):

    # variants count case/control on samples update
    conn.execute(
        """
        CREATE TRIGGER IF NOT EXISTS count_after_update_on_samples AFTER UPDATE ON samples
        WHEN new.phenotype <> old.phenotype
        BEGIN
            UPDATE variants
            SET 
                case_count_ref = case_count_ref + IIF( new.phenotype = 2 AND (SELECT count(shv.variant_id) FROM genotypes as shv WHERE sample_id=new.id AND variant_id=variants.id AND gt=0) = 1, 1, 0 ) + IIF( old.phenotype = 2 AND (SELECT count(shv.variant_id) FROM genotypes as shv WHERE sample_id=new.id AND variant_id=variants.id AND gt=0) = 1, -1, 0 ),
                
                case_count_het = case_count_het + IIF( new.phenotype = 2 AND (SELECT count(shv.variant_id) FROM genotypes as shv WHERE sample_id=new.id AND variant_id=variants.id AND gt=1) = 1, 1, 0 ) + IIF( old.phenotype = 2 AND (SELECT count(shv.variant_id) FROM genotypes as shv WHERE sample_id=new.id AND variant_id=variants.id AND gt=1) = 1, -1, 0 ),
                
                case_count_hom = case_count_hom + IIF( new.phenotype = 2 AND (SELECT count(shv.variant_id) FROM genotypes as shv WHERE sample_id=new.id AND variant_id=variants.id AND gt=2) = 1, 1, 0 ) + IIF( old.phenotype = 2 AND (SELECT count(shv.variant_id) FROM genotypes as shv WHERE sample_id=new.id AND variant_id=variants.id AND gt=2) = 1, -1, 0 ),

                control_count_ref = control_count_ref + IIF( new.phenotype = 1 AND (SELECT count(shv.variant_id) FROM genotypes as shv WHERE sample_id=new.id AND variant_id=variants.id AND gt=0) = 1, 1, 0 ) + IIF( old.phenotype = 1 AND (SELECT count(shv.variant_id) FROM genotypes as shv WHERE sample_id=new.id AND variant_id=variants.id AND gt=0) = 1, -1, 0 ),
                
                control_count_het = control_count_het + IIF( new.phenotype = 1 AND (SELECT count(shv.variant_id) FROM genotypes as shv WHERE sample_id=new.id AND variant_id=variants.id AND gt=1) = 1, 1, 0 ) + IIF( old.phenotype = 1 AND (SELECT count(shv.variant_id) FROM genotypes as shv WHERE sample_id=new.id AND variant_id=variants.id AND gt=1) = 1, -1, 0 ),
                
                control_count_hom = control_count_hom + IIF( new.phenotype = 1 AND (SELECT count(shv.variant_id) FROM genotypes as shv WHERE sample_id=new.id AND variant_id=variants.id AND gt=2) = 1, 1, 0 ) + IIF( old.phenotype = 1 AND (SELECT count(shv.variant_id) FROM genotypes as shv WHERE sample_id=new.id AND variant_id=variants.id AND gt=2) = 1, -1, 0 )
                
            WHERE variants.id IN (SELECT shv2.variant_id FROM genotypes as shv2 WHERE shv2.sample_id=new.id) ;
        END;
        """
    )

    # variants count validations on genotypes update
    conn.execute(
        """
        CREATE TRIGGER IF NOT EXISTS count_validation_positive_negative_after_update_on_genotypes AFTER UPDATE ON genotypes
        WHEN new.classification <> old.classification
        BEGIN
            UPDATE variants
            SET count_validation_positive = (SELECT count(shv.sample_id) FROM genotypes as shv WHERE shv.variant_id=new.variant_id AND shv.classification>0), 
                count_validation_negative = (SELECT count(shv.sample_id) FROM genotypes as shv WHERE shv.variant_id=new.variant_id AND shv.classification<0),
                count_validation_positive_sample_lock = (SELECT count(shv.sample_id) FROM genotypes as shv INNER JOIN samples as s ON s.id=shv.sample_id WHERE s.classification>0 AND shv.variant_id=new.variant_id AND shv.classification>0), 
                count_validation_negative_sample_lock = (SELECT count(shv.sample_id) FROM genotypes as shv INNER JOIN samples as s ON s.id=shv.sample_id WHERE s.classification>0 AND shv.variant_id=new.variant_id AND shv.classification<0)
            WHERE id=new.variant_id;
        END;
        """
    )

    # variants count validations on samples update
    conn.execute(
        """
        CREATE TRIGGER IF NOT EXISTS count_validation_positive_negative_after_update_on_samples AFTER UPDATE ON samples
        WHEN new.classification <> old.classification
        BEGIN
            UPDATE variants
            SET count_validation_positive_sample_lock = (SELECT count(shv.sample_id) FROM genotypes as shv INNER JOIN samples as s ON s.id=shv.sample_id WHERE s.classification>0 AND shv.variant_id=variants.id AND shv.classification>0), 
                count_validation_negative_sample_lock = (SELECT count(shv.sample_id) FROM genotypes as shv INNER JOIN samples as s ON s.id=shv.sample_id WHERE s.classification>0 AND shv.variant_id=variants.id AND shv.classification<0)
            WHERE id IN (SELECT shv2.variant_id FROM genotypes as shv2 WHERE shv2.sample_id=new.id);
        END;
        """
    )

    # variants count validations on samples update
    conn.execute(
        """
        CREATE TRIGGER IF NOT EXISTS count_validation_positive_negative_variant_after_update_on_genotypes AFTER UPDATE ON genotypes
        WHEN new.classification <> old.classification
        BEGIN
            UPDATE samples
            SET count_validation_positive_variant = (SELECT count(shv.variant_id) FROM genotypes as shv WHERE shv.sample_id=new.sample_id AND shv.classification>0), 
                count_validation_negative_variant = (SELECT count(shv.variant_id) FROM genotypes as shv WHERE shv.sample_id=new.sample_id AND shv.classification<0)
            WHERE id = new.sample_id;
        END;
        """
    )

    ###### trigers for history

    tables_fields_triggered = {
        "variants": ["favorite", "classification", "tags", "comment"],
        "samples": [
            "classification",
            "tags",
            "comment",
            "family_id",
            "father_id",
            "mother_id",
            "sex",
            "phenotype",
        ],
        "genotypes": ["tags", "comment"],
    }

    for table in tables_fields_triggered:

        for field in tables_fields_triggered[table]:

            conn.execute(
                f"""
                CREATE TRIGGER IF NOT EXISTS history_{table}_{field}
                AFTER UPDATE ON {table}
                WHEN old.{field} !=  new.{field}
                BEGIN
                    INSERT INTO history (
                        `user`,
                        `table`,
                        `table_rowid`,
                        `field`,
                        `before`,
                        `after`
                    )
                VALUES
                    (
                    current_user(),
                    "{table}",
                    new.rowid,
                    "{field}",
                    old.{field},
                    new.{field}
                    ) ;
                END;"""
            )


def create_database_schema(conn: sqlite3.Connection, fields: Iterable[dict] = None):

    if fields is None:
        # get mandatory fields
        fields = list(get_clean_fields())

    create_table_project(conn)
    # Create metadatas
    create_table_metadatas(conn)
    # Create table fields
    create_table_fields(conn)

    # Create variants tables
    variant_fields = (i for i in fields if i["category"] == "variants")
    create_table_variants(conn, variant_fields)

    # Create annotations tables
    ann_fields = (i for i in fields if i["category"] == "annotations")
    create_table_annotations(conn, ann_fields)

    # # Create table samples
    sample_fields = (i for i in fields if i["category"] == "samples")
    create_table_samples(conn, sample_fields)

    # # Create selection
    create_table_selections(conn)

    # # Create table sets
    create_table_wordsets(conn)

    ## Create table history
    create_table_history(conn)

    ## Create table tags
    create_table_tags(conn)

    ## Create triggers
    create_triggers(conn)


def import_reader(
    conn: sqlite3.Connection,
    reader: AbstractReader,
    pedfile: str = None,
    import_id: str = None,
    ignored_fields: list = [],
    indexed_fields: list = [],
    progress_callback: Callable = None,
):

    tables = ["variants", "annotations", "genotypes"]
    fields = get_clean_fields(reader.get_fields())
    fields = get_accepted_fields(fields, ignored_fields)

    # If shema exists, create a database schema
    if not schema_exists(conn):
        LOGGER.debug("CREATE TABLE SCHEMA")
        create_database_schema(conn, fields)
    else:
        alter_table_from_fields(conn, fields)

    # Update metadatas
    update_metadatas(conn, reader.get_metadatas())

    # insert samples
    if progress_callback:
        progress_callback("Insert samples")
    if reader.filename:
        import_vcf = os.path.basename(reader.filename)
    else:
        import_vcf = None
    insert_samples(conn, samples=reader.get_samples(), import_id=import_id, import_vcf=import_vcf)

    # insert ped
    if pedfile:
        if progress_callback:
            progress_callback("Insert pedfile")
        import_pedfile(conn, pedfile)

    # insert fields
    insert_fields(conn, fields)

    # insert variants
    # Create index for annotation ( performance reason)
    if progress_callback:
        progress_callback("Insert variants. This can take a while")
    create_annotations_indexes(conn)
    insert_variants(
        conn,
        get_clean_variants(reader.get_variants()),
        total_variant_count=reader.number_lines,
        progress_callback=progress_callback,
        progress_every=1000,
    )

    # create index
    if progress_callback:
        progress_callback("Indexation. This can take a while")

    vindex = {field["name"] for field in indexed_fields if field["category"] == "variants"}
    aindex = {field["name"] for field in indexed_fields if field["category"] == "annotations"}
    sindex = {field["name"] for field in indexed_fields if field["category"] == "samples"}

    try:
        create_indexes(conn, vindex, aindex, sindex, progress_callback=progress_callback)
    except:
        LOGGER.info("Index already exists")

    # update variants count
    if progress_callback:
        progress_callback("Variants counts. This can take a while")
    update_variants_counts(conn, progress_callback)

    # database creation complete
    if progress_callback:
        progress_callback("Database creation complete")


def export_writer(
    conn: sqlite3.Connection,
    writer: AbstractWriter,
    progress_callback: Callable = None,
):
    pass


def import_pedfile(conn: sqlite3.Connection, filename: str):

    if os.path.isfile(filename):
        for sample in PedReader(filename, get_samples(conn), raw_samples=False):
            update_sample(conn, sample)


# def from_reader(conn, reader: AbstractReader, progress_callback=None):
#     # si base pas construite : construire

#     # import samples
#     # import fields
#     pass


# def to_writer(conn, writer: AbstractWriter):
#     pass
