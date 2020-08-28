"""This Modules bringing together all the SQL related functions
to read and write the sqlite database with the schema describe here.
Each method refer to a CRUD operation using following prefixes:
``get_``, ``insert_``, ``update_``, ``remove_`` and take a sqlite connexion as ``conn`` attribut.

The module contains also QueryBuilder class to build complexe variant query based on
filters,columns and selection.

Example::

    # Read sample table information
    from cutevariant.core import sql
    conn = sql.get_sql_connexion("project.db")
    sql.get_samples(conn)

    # Build a variant query
    from cutevariant.core import sql
    conn = sql.get_sql_connexion("project.db")
    builder = QueryBuilder(conn)
    builder.columns = ["chr","pos","ref","alt"]
    print(builder.sql())

"""

# Standard imports
import sqlite3
import sys
from collections import defaultdict
from pkg_resources import parse_version
from functools import lru_cache
import re

# Custom imports
import cutevariant.commons as cm
import logging

LOGGER = cm.logger()


## ================ Misc functions ====================================


def get_sql_connexion(filepath):
    """Open a SQLite database and return the connexion object

    Args:
        filepath (str): sqlite filepath

    Returns:
        sqlite3.Connection: Sqlite3 Connection
    """
    connexion = sqlite3.connect(filepath)
    # Activate Foreign keys
    connexion.execute("PRAGMA foreign_keys = ON")
    connexion.row_factory = sqlite3.Row
    foreign_keys_status = connexion.execute("PRAGMA foreign_keys").fetchone()[0]
    LOGGER.debug("get_sql_connexion:: foreign_keys state: %s", foreign_keys_status)
    assert foreign_keys_status == 1, "Foreign keys can't be activated :("

    # Create function for sqlite
    def regexp(expr, item):
        reg = re.compile(expr)
        return reg.search(item) is not None

    connexion.create_function("REGEXP", 2, regexp)

    return connexion


def drop_table(conn, table_name):
    """Drop the given table

    Args:
        conn (sqlite3.connexion): Sqlite3 connexion
        table_name (str): sqlite table name
    """
    cursor = conn.cursor()
    cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
    conn.commit()


def clear_table(conn: sqlite3.Connection, table_name):
    """Clear content of the given table

    Args:
        conn (sqlite3.Connection): Sqlite3 Connection
        table_name (str): sqlite table name
    """
    cursor = conn.cursor()
    cursor.execute(f"DELETE  FROM {table_name}")
    conn.commit()


def get_columns(conn: sqlite3.Connection, table_name):
    """Return the list of columns for the given table

    Args:
        conn (sqlite3.Connection): Sqlite3 Connection
        table_name (str): sqlite table name

    Returns:
        Columns description from table_info
        ((0, 'chr', 'str', 0, None, 1 ... ))

    References:
        used by async_insert_many_variants() to build queries with placeholders

    Todo:
        Rename to get_table_columns

    """
    return [
        c[1] for c in conn.execute(f"pragma table_info({table_name})") if c[1] != "id"
    ]


def create_indexes(conn: sqlite3.Connection):
    """Create extra indexes on tables

    Args:
        conn (sqlite3.Connection): Sqlite3 Connection

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


## ================ PROJECT TABLE ===================================


def create_project(conn: sqlite3.Connection, name: str, reference: str):
    """Create the table "projects" and insert project name and reference genome

    Args:
        conn (sqlite3.Connection): Sqlite3 Connection
        name (str): Project name
        reference (str): Genom project

    Todo:
        * Rename to create_table_project

    """
    cursor = conn.cursor()
    cursor.execute(
        """CREATE TABLE projects (id INTEGER PRIMARY KEY, name TEXT, reference TEXT)"""
    )
    cursor.execute(
        """INSERT INTO projects (name, reference) VALUES (?, ?)""", (name, reference)
    )
    conn.commit()


def create_table_metadatas(conn: sqlite3.Connection):
    """Create table metdata
    
    Args:
        conn (sqlite3.Connection): Description
    """
    cursor = conn.execute(
        """CREATE TABLE metadatas (id INTEGER PRIMARY KEY, key TEXT, value TEXT)"""
    )


def insert_many_metadatas(conn: sqlite3.Connection, metadatas={}):
    """Insert metadata 
    
    Args:
        conn (sqlite3.Connection): Description
    """
    if metadatas:
        conn.executemany(
            """
            INSERT INTO metadatas (key,value)
            VALUES (?,?)
            """,
            list(metadatas.items()),
        )

        conn.commit()


## ================ SELECTION TABLE ===================================


def create_table_selections(conn: sqlite3.Connection):
    """Create the table "selections" and association table "selection_has_variant"

    This table stores variants selection saved by the user:
            - name: name of the set of variants
            - count: number of variants concerned by this set
            - query: the SQL query which generated the set

        :param conn: sqlite3.connect

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
    """Create indexes on the "selections" table

    Args:
        conn (sqlite3.Connection): Sqlite3 Connection

    Note:
        * This function should be called after batch insertions.
        * This function ensures the unicity of selections names.
    """
    conn.execute("""CREATE UNIQUE INDEX idx_selections ON selections (name)""")


def create_selection_has_variant_indexes(conn: sqlite3.Connection):
    """Create indexes on "selection_has_variant" table
    For joints between selections and variants tables

    Reference:
        * create_selections_indexes()
        * insert_selection()

    Args:
        conn (sqlite3.Connection): Sqlite3 connection
    """
    #
    conn.execute(
        """CREATE INDEX idx_selection_has_variant ON selection_has_variant (selection_id)"""
    )


def insert_selection(conn, query: str, name="no_name", count=0):
    """Insert one selection record

    Args:
        conn (sqlite3.Connection): Sqlite3 Connection.It can be a cursor or a connection here...
        query (str): a VQL query
        name (str, optional): Name of selection
        count (int, optional): Variant count of selection

    Returns:
        int: Return last rowid

    See Also:
        create_selection_from_sql()

    Warning:
        This function does a commit !


    """
    cursor = conn.cursor() if isinstance(conn, sqlite3.Connection) else conn

    cursor.execute(
        """INSERT INTO selections (name, count, query) VALUES (?,?,?)""",
        (name, count, query),
    )
    if isinstance(conn, sqlite3.Connection):
        # Commit only if connection is given. => avoid not consistent DB
        conn.commit()
    return cursor.lastrowid


def delete_selection_by_name(conn: sqlite3.Connection, name: str):
    """Delete selection from name

    Args:
        conn (sqlit3.Connection): sqlite3 connection
        name (str): selection name

    Returns:
        TYPE: Description
    """

    if name == "variants":
        LOGGER.error("Cannot remove variants")
        return

    cursor = conn.cursor()
    cursor.execute(f"DELETE FROM selections WHERE name = ?", (name,))
    conn.commit()


def create_selection_from_sql(
    conn: sqlite3.Connection, query: str, name: str, count=None, from_selection=False
):
    """Create a selection record from sql variant query

    Args:
        conn (sqlite3.connexion): Sqlite3 connexion
        query (str): VQL query
        name (str): Name of selection
        count (int, optional): Variant count
        from_selection (bool, optional): selection name
    """
    cursor = conn.cursor()

    # Compute query count
    #  TODO : this can take a while .... need to compute only one from elsewhere
    if not count:
        count = cursor.execute(f"SELECT COUNT(*) FROM ({query})").fetchone()[0]

    # Create selection
    selection_id = insert_selection(cursor, query, name=name, count=count)

    # DROP indexes
    # For joints between selections and variants tables
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

    # REBUILD INDEXES
    # For joints between selections and variants tables
    create_selection_has_variant_indexes(cursor)

    conn.commit()
    if cursor.rowcount:
        return cursor.lastrowid
    return None


def create_selection_from_bed(
    conn: sqlite3.Connection, source: str, target: str, bed_intervals
):
    """Create a new selection based on the given intervals taken from a BED file

    Args:
        conn (sqlite3.connexion): Sqlite3 connexion
        source (str): Selection name (source)
        target (str): Selection name (target)
        bed_intervals (list): List of interval (begin,end)

    Returns:
        TYPE: Description

    """

    cur = conn.cursor()

    #  Create temporary table
    cur.execute("DROP TABLE IF exists bed_table")
    cur.execute(
        """CREATE TABLE bed_table (

        id INTEGER PRIMARY KEY ASC, 
        bin INTEGER DEFAULT 0, 
        chr TEXT, 
        start INTEGER, 
        end INTEGER,
        name INTEGER )"""
    )

    for interval in bed_intervals:

        cur.execute(
            "INSERT INTO bed_table (bin, chr, start, end, name) VALUES (?,?,?,?,?)",
            (0, interval["chr"], interval["start"], interval["end"], interval["name"]),
        )

    if source == "variants":
        source_query = "SELECT variants.id as variant_id FROM variants"
    else:
        source_query = """
        SELECT variants.id as variant_id FROM variants
        INNER JOIN selections ON selections.name = '{}'
        INNER JOIN selection_has_variant sv ON sv.variant_id = variants.id AND sv.selection_id = selections.id
        """.format(
            source
        )

    query = (
        source_query
        + """  
                INNER JOIN bed_table ON 
                variants.chr = bed_table.chr AND 
                variants.pos >= bed_table.start AND 
                variants.pos <= bed_table.end """
    )

    return create_selection_from_sql(conn, query, target, from_selection=True)


def get_selections(conn: sqlite3.Connection):
    """Get selections in "selections" table

    Args:
        conn (sqlite3.connexion): Sqlite3 connexion

    Yield:
        Dictionnaries with as many keys as there are columnsin the table.

    Example::
        {"id": ..., "name": ..., "count": ..., "query": ...}

    """
    conn.row_factory = sqlite3.Row
    return (dict(data) for data in conn.execute("""SELECT * FROM selections"""))


def delete_selection(conn: sqlite3.Connection, selection_id: int):
    """Delete the selection with the given id in the "selections" table

    :return: Number of rows deleted
    :rtype: <int>

    Args:
        conn (sqlite3.Connection): Sqlite connection
        selection_id (int): id from selection table

    Returns:
        int: last rowid
    """
    cursor = conn.cursor()
    cursor.execute("DELETE FROM selections WHERE rowid = ?", (selection_id,))
    conn.commit()
    return cursor.rowcount


def edit_selection(conn: sqlite3.Connection, selection: dict):
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


## ================ Create sets tables =========================================


def create_table_sets(conn: sqlite3.Connection):
    """Create the table "sets" 
    
    This table stores variants selection saved by the user:
            - name: name of the set of variants
            - value: number of variants concerned by this set

    Args:
        conn (sqlite3.Connection): Sqlite3 Connection
    """
    cursor = conn.cursor()
    # selection_id is an alias on internal autoincremented 'rowid'
    cursor.execute(
        """CREATE TABLE sets (
        id INTEGER PRIMARY KEY ASC,
        name TEXT, 
        value TEXT
        )"""
    )

    conn.commit()


def insert_set_from_file(conn: sqlite3.Connection, name, filename):

    cursor = conn.cursor()
    # TODO ignore duplicate 
    with open(filename) as file:
        cursor.executemany(
            """INSERT INTO sets (name, value) VALUES (?,?)""",
            ((name, i.strip()) for i in file),
        )

    conn.commit()


def get_sets(conn):
    """ Get sets """
    for row in conn.execute(
        "SELECT name , COUNT(*) as 'count' FROM sets GROUP BY name"
    ):
        yield dict(row)


def get_words_set(conn, name):
    """ Get word from sets """ 
    for row in conn.execute(
        f"SELECT DISTINCT value FROM sets WHERE name = '{name}'"
    ):
        yield dict(row)["value"]




## ================ Operations on sets of variants =============================


def get_query_columns(mode="variant"):
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


def intersect_variants(query1, query2, **kwargs):
    """Get the variants obtained by the intersection of 2 queries
    Try to handl precedence of operators.
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


## ================ Fields functions ===========================================


def create_table_fields(conn):
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
        (id INTEGER PRIMARY KEY, name TEXT, category TEXT, type TEXT, description TEXT)
        """
    )
    conn.commit()


def insert_field(
    conn, name="no_name", category="variants", type="text", description=str()
):
    """Insert one field record (NOT USED)

    :param conn: sqlite3.connect
    :key name: field name
    :key category: category field name.
        .. warning:: The default is "variants". Don't use sample as category name
    :key type: sqlite type which can be: INTEGER, REAL, TEXT
        .. todo:: Check this argument...
    :key description: Text that describes the field (showed to the user).
    :return: Last row id
    :rtype: <int>
    """
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO fields VALUES (?, ?, ?, ?)
        """,
        (name, category, type, description),
    )
    conn.commit()
    return cursor.lastrowid


def insert_many_fields(conn, data: list):
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
        INSERT INTO fields (name,category,type,description)
        VALUES (:name,:category,:type,:description)
        """,
        data,
    )
    conn.commit()


def get_fields(conn):
    """Get fields as list of dictionnary

    .. seealso:: insert_many_fields

    :param conn: sqlite3.connect
    :return: Generator of dictionnaries with as many keys as there are columns
        in the table.
    :rtype: <generator <dict>>
    """
    conn.row_factory = sqlite3.Row
    return (dict(data) for data in conn.execute("""SELECT * FROM fields"""))


def get_field_by_category(conn, category):
    """ Get fields within a category

    :param conn: sqlite3.connect
     :return: Generator of dictionnaries with as many keys as there are columns
        in the table.
    :rtype: <generator <dict>>
    """

    return [field for field in get_fields(conn) if field["category"] == category]


def get_field_by_name(conn, field_name: str):
    """ Return field by his name

    .. seealso:: get_fields

    :param conn: sqlite3.connect
    :param field_name (str): field name
    :return: field record
    :rtype: <dict>
    """
    conn.row_factory = sqlite3.Row
    return dict(
        conn.execute(
            """SELECT * FROM fields WHERE name = ? """, (field_name,)
        ).fetchone()
    )


def get_field_range(conn, field_name: str, sample_name=None):
    """ Return (min,max) of field_name records .

    :param conn: sqlite3.connect
    :param field_name (str): field name
    :param sample_name (str): sample name. mandatory for fields in the "samples" categories
    :return: (min, max)
    :rtype: tuple
    """
    field = get_field_by_name(conn, field_name)
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
        query = f"""SELECT min({field_name}), max({field_name}) FROM {table}"""

    result = tuple(conn.execute(query).fetchone())
    if result == (None, None):
        return None
    if result == ("", ""):
        return None

    return result


def get_field_unique_values(conn, field_name: str, sample_name=None):
    """ Return unique record value for a field name

    :param conn: sqlite3.connect
    :param field_name (str): field_name
    :param sample_name (str): sample name. mandatory for fields in the "samples" categories
    :return: list of unique values
    :rtype: list
    """
    field = get_field_by_name(conn, field_name)
    table = field["category"]  # variants, or annotations or samples
    if table == "samples":
        if not sample_name:
            raise ValueError("Pass sample parameter for sample fields")
        query = f"""SELECT DISTINCT {field_name}
        FROM sample_has_variant
        JOIN samples ON sample_has_variant.sample_id = samples.id
        WHERE samples.name='{sample_name}'
        """
    else:
        query = f"""SELECT DISTINCT `{field_name}` FROM {table}"""
    return [i[field_name] for i in conn.execute(query)]


## ================ Annotations functions ======================================


def create_table_annotations(conn, fields):
    """Create "annotations" table which contains dynamics fields

    :param fields: Generator of SQL fields.
        :Example of fields:
            ('allele str NULL', 'consequence str NULL', ...)
    :type fields: <generator>
    """
    schema = ",".join([f'`{field["name"]}` {field["type"]}' for field in fields])

    if not schema:
        #  Create minimum annotation table... Can be use later for dynamic annotation.
        # TODO : we may want to fix annotation fields .
        schema = "gene TEXT, transcript TEXT"
        LOGGER.debug(
            "create_table_annotations:: No annotation fields detected! => Fallback"
        )
        # return

    cursor = conn.cursor()
    # TODO: no primary key/unique index for this table?

    cursor.execute(
        f"""CREATE TABLE annotations (variant_id INTEGER NOT NULL, {schema})"""
    )

    conn.commit()


def create_annotations_indexes(conn):
    """Create indexes on the "annotations" table

    .. warning: This function must be called after batch insertions.

    :Example:
        SELECT *, group_concat(annotations.rowid) FROM variants
        LEFT JOIN annotations ON variants.rowid = annotations.variant_id
        WHERE pos = 0
        GROUP BY chr,pos
        LIMIT 100
    """

    # Allow search on variant_id
    conn.execute("""CREATE INDEX idx_annotations ON annotations (variant_id)""")


## ================ Variants functions =========================================


def create_table_variants(conn, fields):
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


def create_variants_indexes(conn):
    """Create indexes on the "variants" table

    .. warning: This function must be called after batch insertions.

    :Example:
        SELECT *, group_concat(annotations.rowid) FROM variants
        LEFT JOIN annotations ON variants.rowid = annotations.variant_id
        WHERE pos = 0
        GROUP BY chr,pos
        LIMIT 100
    """

    # Complementary index of the primary key (sample_id, variant_id)
    conn.execute(
        """CREATE INDEX idx_sample_has_variant ON sample_has_variant (variant_id)"""
    )

    conn.execute("""CREATE INDEX idx_variants_pos ON variants (pos)""")
    conn.execute("""CREATE INDEX idx_variants_ref_alt ON variants (ref, alt)""")


def get_one_variant(conn, id: int):
    """Get the variant with the given id"""
    # Use row_factory here
    conn.row_factory = sqlite3.Row
    # Cast sqlite3.Row object to dict because later, we use items() method.
    return dict(
        conn.execute(f"""SELECT * FROM variants WHERE variants.id = {id}""").fetchone()
    )


def update_variant(conn, variant: dict):
    """ Update variant data """

    sql_set = []
    sql_val = []
    for key, value in variant.items():
        if key != "id":
            sql_set.append(f"`{key}` = ? ")
            sql_val.append(value)

    query = (
        "UPDATE variants SET " + ",".join(sql_set) + " WHERE id = " + str(variant["id"])
    )
    conn.execute(query, sql_val)
    conn.commit()


def get_annotations(conn, id: int):
    """ Get variant annotation with the given id """
    conn.row_factory = sqlite3.Row
    for annotation in conn.execute(
        f"""SELECT * FROM annotations WHERE variant_id = {id}"""
    ):
        yield dict(annotation)


def get_sample_annotations(conn, variant_id: int, sample_id: int):
    """ Get variant annotation for a given sample """
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    q = f"""SELECT * FROM sample_has_variant WHERE variant_id = {variant_id} and sample_id = {sample_id}"""
    result = cursor.execute(
        f"""SELECT * FROM sample_has_variant WHERE variant_id = {variant_id} and sample_id = {sample_id}"""
    ).fetchone()

    return dict(result)


def get_variants_count(conn):
    """Get the number of variants in the "variants" table"""
    return conn.execute("""SELECT COUNT(*) FROM variants""").fetchone()[0]


def async_insert_many_variants(conn, data, total_variant_count=None, yield_every=3000):
    """Insert many variants from data into variants table

    :param conn: sqlite3.connect
    :param data: list of variant dictionnary which contains same number of key than fields numbers.
    :param variant_count: total variant count, to compute progression
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

    .. warning:: About using INSERT OR IGNORE:
        INSERT OR IGNORE avoids errors:

            - Upon insertion of a duplicate key where the column must contain
            a PRIMARY KEY or UNIQUE constraint
            - Upon insertion of NULL value where the column has
            a NOT NULL constraint.
        => This is not recommended
    """

    def build_columns_and_placeholders(table_name):
        """Build a tuple of columns and "?" placeholders for INSERT queries
        """
        # Get columns description from the given table
        cols = get_columns(conn, table_name)
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

    var_columns = get_columns(conn, "variants")
    ann_columns = get_columns(conn, "annotations")
    sample_columns = get_columns(conn, "sample_has_variant")

    # Get samples with samples names as keys and sqlite rowid as values
    # => used as a mapping for samples ids
    samples_id_mapping = {
        name: rowid for name, rowid in conn.execute("SELECT name, id FROM samples")
    }
    samples_names = samples_id_mapping.keys()

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
    for variant_count, variant in enumerate(data, 1):

        # Insert current variant
        # Use default dict to handle missing values
        #LOGGER.debug(
        #    "async_insert_many_variants:: QUERY: %s\nVALUES: %s",
        #    variant_insert_query,
        #    variant,
        # )

        #  Create list of value to insert
        # ["chr",234234,"A","G"]
        default_values = defaultdict(str, variant)
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
                default_values = defaultdict(str, ann)
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
            # TODO: is this test usefull since samples that are in the database
            # have been inserted from the same source file (or it is not the case ?) ?
            # Retrieve the id of the sample to build the association in
            # "sample_has_variant" table carrying the data "gt" (genotype)

            samples = []
            for sample in variant["samples"]:
                sample_id = samples_id_mapping[sample["name"]]
                default_values = defaultdict(str, sample)
                sample_value = [sample_id, variant_id]
                sample_value += [default_values[i] for i in sample_columns[2:]]
                samples.append(sample_value)

            placeholder = ",".join(["?"] * len(sample_columns))

            q = f"""INSERT INTO sample_has_variant VALUES ({placeholder})"""
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
    for _, _ in async_insert_many_variants(conn, data, kwargs):
        pass


## ================ Samples functions ==========================================


def create_table_samples(conn, fields=None):
    """Create samples table

    :param conn: sqlite3.connect
    """
    cursor = conn.cursor()
    # sample_id is an alias on internal autoincremented 'rowid'
    cursor.execute(
        """CREATE TABLE samples (
        id INTEGER PRIMARY KEY ASC,
        name TEXT,
        fam TEXT DEFAULT 'fam',
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


def insert_sample(conn, name="no_name"):
    """Insert one sample in samples table (USED in TESTS)

    :param conn: sqlite3.connect
    :return: Last row id
    :rtype: <int>
    """
    cursor = conn.cursor()
    cursor.execute("""INSERT INTO samples (name) VALUES (?)""", [name])
    conn.commit()
    return cursor.lastrowid


def insert_many_samples(conn, samples: list):
    """Insert many samples at a time in samples table

    :param samples: List of samples names
        .. todo:: only names in this list ?
    :type samples: <list <str>>
    """
    cursor = conn.cursor()
    cursor.executemany(
        """INSERT INTO samples (name) VALUES (?)""", ((sample,) for sample in samples)
    )
    conn.commit()


def get_samples(conn):
    """"Get samples from sample table

    :param con: sqlite3.conn
    :return: Generator of dictionnaries with as sample fields as values.
        :Example: ({'id': <unique_id>, 'name': <sample_name>})
    :rtype: <generator <dict>>
    """
    conn.row_factory = sqlite3.Row
    return (dict(data) for data in conn.execute("""SELECT * FROM samples"""))


def update_sample(conn, sample: dict):
    """Update sample record

    sample = {
        id : 3 # sample id
        name : "Boby",  # Name of sample
        fam : "fam", # familly identifier
        father_id : 0, # father id, 0 if not
        mother_id : 0, # mother id, 0 if not
        sex : 0 # sex code ( 1 = male, 2 = female, 0 = unknown)
        phenotype: 0 # ( 1 = control , 2 = case, 0 = unknown)
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


def count_query(conn, query):
    """ count from query """
    print(query)
    return conn.execute(f"SELECT COUNT(*) as count FROM ({query})").fetchone()[0]


# ======================== execute commande ======================================
