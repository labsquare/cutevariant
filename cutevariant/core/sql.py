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


## ================ SELECTION TABLE ===================================

def create_table_selections(conn:sqlite3.Connection):
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


def create_selection_from_bed(conn: sqlite3.Connection, source: str, target: str, bed_intervals):
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
        chrom TEXT, 
        start INTEGER, 
        end INTEGER,
        name INTEGER )"""
    )

    for interval in bed_intervals:
        cur.execute(
            "INSERT INTO bed_table (bin, chrom, start, end, name) VALUES (?,?,?,?,?)",
            (
                0,
                interval["chrom"],
                interval["start"],
                interval["end"],
                interval["name"],
            ),
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
                variants.chr = bed_table.chrom AND 
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


def edit_selection(conn:sqlite3.Connection, selection: dict):
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


def get_field_range(conn, field_name: str):
    """ Return (min,max) of field_name records . 
    
    :param conn: sqlite3.connect
    :param field_name (str): field name
    :return: (min, max) 
    :rtype: tuple
    """
    field = get_field_by_name(conn, field_name)
    table = field["category"]  # variants, or annotations or samples
    query = f"""SELECT min({field_name}), max({field_name}) FROM {table}"""

    result = tuple(conn.execute(query).fetchone())
    if result == (None, None):
        return None
    if result == ("", ""):
        return None

    return result


def get_field_unique_values(conn, field_name: str):
    """ Return unique record value for a field name 

    :param conn: sqlite3.connect 
    :param field_name (str): field_name
    :return: list of unique values
    :rtype: list
    """
    field = get_field_by_name(conn, field_name)
    table = field["category"]  # variants, or annotations or samples
    # conn.row_factory = None
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
    schema = ",".join([f'{field["name"]} {field["type"]}' for field in fields])

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

    query = "UPDATE variants SET " + ",".join(sql_set) + " WHERE id = " + str(variant["id"])
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
        LOGGER.debug(
            "async_insert_many_variants:: QUERY: %s\nVALUES: %s",
            variant_insert_query,
            variant,
        )

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
        sexe INTEGER DEFAULT 0,
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
        schema = 'gt INTEGER DEFAULT DEFAULT -1'

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
        sexe : 0 # Sexe code ( 1 = male, 2 = female, 0 = unknown)
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

    query = "UPDATE samples SET " + ",".join(sql_set) + " WHERE id = " + str(sample["id"])
    conn.execute(query, sql_val)
    conn.commit()
## ============== VARIANTS QUERY THINGS ... ======================
from cutevariant.core.vql import execute_vql

class QueryBuilder(object):
    """A class to Create a variant Selection query 
    """

    _GENOTYPE_FUNCTION_NAME = "genotype"
    _PHENOTYPE_FUNCTION_NAME = "phenotype"
    _VARIANT_TABLE = "variants"

    def __init__(
        self,
        conn,
        columns=["chr", "pos", "ref", "alt"],
        filters=dict(),
        selection="variants",
        order_by=None,
        order_desc=True,
    ):
        """Create an instance with different parameters 

        See:
            sql.build_variant_query
        
        Args:
            conn (sqlite): sqlite3 connection database
            columns (list, optional): Columns selections. Defaults to ["chr", "pos", "ref", "alt"].
            filters (dict, optional): Filter as a nested dictionnary. Defaults to dict().
            selection (str, optional): Source table. Defaults to "variants".
            order_by (str, optional): Order by column. Defaults to None.
            order_desc (bool, optional): Sort result in descendant order. Defaults to True.
        """

        self.conn = conn
        self.columns = columns
        self.filters = filters
        self.selection = selection
        self.order_by = order_by
        self.order_desc = order_desc

    @property
    def conn(self):
        return self._conn

    @conn.setter
    def conn(self, conn):
        self._conn = conn
        # Read those data only once from sqliute
        self.cache_annotations_columns = get_columns(conn, "annotations")
        self.cache_variants_columns = get_columns(conn, "variants")

        #  Read samples and make possible to map the sample id from the sample name
        self.cache_samples_ids = dict([(i["name"], i["id"]) for i in get_samples(conn)])

    @staticmethod
    def _filters_to_flat(filters: dict):
        """Recursive function to convert the filter hierarchical dictionnary into a list of fields

        Args:
            filter (dict): a nested tree of condition. @See example

        Returns:
            Return (list): all field are now inside a a list 

        Todo:
            Move to vql ? 

        Examples:
            filters = {'AND': 
            [{'field': 'ref', 'operator': '=', 'value': "A"},
            {'field': 'alt', 'operator': '=', 'value': "C"}]
            }
            
            filters = _flatten_filter(filters)

            # filters is now [{'field': 'ref', 'operator': '=', 'value': "A"},{'field': 'alt', 'operator': '=', 'value': "C"}]] 
        """

        if isinstance(filters, dict) and len(filters) == 3:
            yield filters

        if isinstance(filters, dict):
            for i in filters:
                yield from QueryBuilder._filters_to_flat(filters[i])

        if isinstance(filters, list):
            for i in filters:
                yield from QueryBuilder._filters_to_flat(i)

    def _filters_to_sql(self, node: dict, format_sql = True):
        """Recursive function to convert the filter hierarchical dictionnary into a SQL WHERE clause.
        
        Args:
            filters (dict): a nested tree of condition. @See example

        Returns:
            Return (str): a Sql Where clause
        
        """

        if not node:
            return ""

        # Function to detect IF node is a Condition node (AND/OR)
        # OR a field node with (name, operator, value) as keys
        is_field = lambda x: True if len(x) == 3 else False

        if is_field(node):
            # print("IS FIELD", node)

            # Process value
            value = node["value"]
            operator = node["operator"]
            field = node["field"]

            if type(value) == str:
                value = f"'{value}'"

            if format_sql:
                # Format for SQL 
                field = self.column_to_sql(field, use_alias=False)

            # convert (genotype,sample,field) to genotype(sample).field
            if isinstance(field,tuple):
                field = "{}(\"{}\").{}".format(*field)
        
            # TODO ... c'est degeulasse ....
            if operator in ("IN", "NOT IN"):
                # DO NOT enclose value in quotes
                # node: {'field': 'ref', 'operator': 'IN', 'value': "('A', 'T', 'G', 'C')"}
                # wanted: ref IN ('A', 'T', 'G', 'C')
                pass

            elif isinstance(value, list):
                value = "(" + ",".join(value) + ")"
            else:
                value = str(value)

            # There must be spaces between these strings because of strings operators (IN, etc.)
            return "%s %s %s" % (field, operator, value)
        else:
            # Not a field: 1 key only: the logical operator
            logic_op = list(node.keys())[0]
            # Recursive call for each field in the list associated to the
            # logical operator.
            # node:
            # {'AND': [
            #   {'field': 'ref', 'operator': 'IN', 'value': "('A', 'T', 'G', 'C')"},
            #   {'field': 'alt', 'operator': 'IN', 'value': "('A', 'T', 'G', 'C')"}
            # ]}
            # Wanted: ref IN ('A', 'T', 'G', 'C') AND alt IN ('A', 'T', 'G', 'C')
            out = [self._filters_to_sql(child, format_sql) for child in node[logic_op]]
            # print("OUT", out, "LOGIC", logic_op)
            # OUT ["refIN'('A', 'T', 'G', 'C')'", "altIN'('A', 'T', 'G', 'C')'"]
            if len(out) == 1:
                return f" {logic_op} ".join(out)
            else:
                return "(" + f" {logic_op} ".join(out) + ")"

    @staticmethod
    def _get_functions(columns, func_name="genotype"):
        """Search and return Column-function (aka 3-tuple) from a list 

            Column-function are tuple of 3 elements to describe a function.
            genotype("TUMOR").GT == > (genotype,TUMOR,GT)
            
            Args:
                columns (list): List of columns
                func_name (str, optional): The name of function. Defaults to "genotype".
            
            Returns:
                list: Return a list of 3-tuple 
            """

        return (col for col in columns if isinstance(col, tuple) and len(col) == 3)

    def column_to_sql(self, column, use_alias=True):
        """ Guess from which table the column belongs to and return a well formated name
        
            Return:
                The table name annotations or variants 
        """ 

        # If column is a function aka tuple : ("genotype", "boby","gt") to "`gt_boby`.gt" to perform SQL JOIN
        if isinstance(column, tuple):
            function_name, arg, field_name = column
            if function_name == QueryBuilder._GENOTYPE_FUNCTION_NAME:
                if use_alias:
                    return f"`gt_{arg}`.`{field_name}` AS `gt_{arg}.{field_name}`"
                else:
                    return f"`gt_{arg}`.`{field_name}`"

        if column.startswith("variants.") or column in self.cache_variants_columns:
            column = column.replace("variants.","")
            return f"`variants`.`{column}`"

        if column.startswith("annotations.") or column in self.cache_annotations_columns:
            column = column.replace("annotations.","")
            return f"`annotations`.`{column}`"
        
   

        return column

    def get_table_of_column(self, column):
        """Return table's name of a specific column
        
        Args:
            column (str): column name
        
        Returns:
            str: table name ( samples, annnotations, variants)
        """
        if isinstance(column, tuple):
            return "samples"

        if column.startswith("annotations.") or column in self.cache_annotations_columns:
            return "annotations"

        if column.startswith("variants.") or column in self.cache_variants_columns:
            return "variants"

        return None


    def headers(self):
        """ Return a clean list of columns 

        It returns self.columns by replacing function tuple by a string

        Returns:
            (list): a list of string with well formated column name and variant.id
        """
        headers = ["id"]
        for column in self.columns:
            if isinstance(column, tuple):
                headers.append("{}:{}:{}".format(*column))
            else:
                headers.append(column)
        
        return headers

    def build_sql(
        self,
        columns,
        filters,
        selection = "variants",
        order_by=None,
        order_desc=True,
        grouped = False,
        limit=20,
        offset=0,
    ):
        """Build a SQL Select statement from internal parameters columns, filters, selections.
        see items() and tree() methods
        
        Args:
            columns (list): Columns to be used in SELECT statement
            filters (dict): A nested tree to be used in WHERE statement
            selection (str): Source of the virtual table ( variants or build a joint )
            order_by (str, optional): ORDER BY statement. Defaults to None.
            order_desc (bool, optional): ORDER DESC is it's True. Defaults to True.
            group_by (list, optional): List of columns to group. Defaults to None.
            limit (int, optional): LIMIT SQL statement for record per page. Defaults to 20.
            offset (int, optional): OFFSET SQL statement for page number. Defaults to 0.
        
        Returns:
            [type]: [description]
        """

        #  Build Select statement
        sql_query = ""

        #  Add columns
        sql_columns = ["`variants`.`id`"] + [self.column_to_sql(col) for col in columns]
        sql_query = f"SELECT {','.join(sql_columns)} "

        # Add child count if grouped 
        if grouped:
            sql_query += ", COUNT(*) as `children`"

        #  Add source table
        sql_query += f"FROM variants"

        #  Add Join Annotations
        columns_in_filters = [i["field"] for i in self._filters_to_flat(filters)]
        
        # Loop over columns and check is annotations is required 
        need_join_annotations = False
        for col in columns + columns_in_filters:
            if self.get_table_of_column(col) == "annotations":
                need_join_annotations = True
                break

        if need_join_annotations:
            sql_query += (
                " LEFT JOIN annotations ON annotations.variant_id = variants.id"
            )

        #  Add Join Selection
        # TODO: set variants as global variables
        if selection != "variants":
            sql_query += (
                " INNER JOIN selection_has_variant sv ON sv.variant_id = variants.id "
                f"INNER JOIN selections s ON s.id = sv.selection_id AND s.name = '{selection}'"
            )

        #  Add Join Samples
        ## detect if columns contains function like (genotype,TUMOR,gt)
        all_columns = columns_in_filters + columns
        samples_in_query = set([fct[1] for fct in self._get_functions(all_columns)])
        ## Create Sample Join
        for sample_name in samples_in_query:
            sample_id = self.cache_samples_ids[sample_name]
            sql_query += (
                f" LEFT JOIN sample_has_variant `gt_{sample_name}`"
                f" ON `gt_{sample_name}`.variant_id = variants.id"
                f" AND `gt_{sample_name}`.sample_id = {sample_id}"
            )

        #  Add Where Clause
        if filters:
            where_clause = self._filters_to_sql(filters)
            # TODO : filter_to_sql should returns empty instead of ()
            if where_clause and where_clause != "()":
                sql_query += " WHERE " + where_clause

        #  Add Group By
        if grouped:
            sql_query += " GROUP BY " + ",".join(["chr","pos","ref","alt"])

        #  Add Order By
        if order_by:
            # TODO : sqlite escape field with quote
            orientation = "DESC" if order_desc else "ASC"
            order_by = self.column_to_sql(order_by)
            sql_query += f" ORDER BY {order_by} {orientation}"

        if limit:
            sql_query += f" LIMIT {limit} OFFSET {offset}"

        return sql_query

    def sql(self, grouped = False, limit = 20, offset = 0):
        """Return an SQL Query based on internal parameter columns, filter, selection.
        See _build_sql()

        Args:
            limit(int): Maximum number of variants to display per page
            offset(int): Page number

        """
        return self.build_sql(self.columns, self.filters,self.selection,self.order_by,self.order_desc,grouped,limit,offset)

    def vql(self) -> str:
        """Build a VQL query from the current Query

        Todo : Make it cleaner and test it 

        Return
            A VQL query
        """

        _c = []
        for col in self.columns:
            if isinstance(col, tuple):
                fct, arg, field = col
                if fct == QueryBuilder._GENOTYPE_FUNCTION_NAME:
                    col = f'genotype("{arg}").{field}'
            _c.append(col)

        base = f"SELECT {','.join(_c)} FROM {self.selection}"
        where = ""
        if self.filters:
            where_clause = self._filters_to_sql(self.filters,format_sql = False)
            if where_clause and where_clause != "()":
                where = f" WHERE {where_clause}"
        

        return base + where

    def set_from_vql(self, vql: str):
        """Create a Query from vql 
        
        Args:
            vql (str): vql grammar query 
        """ 

        result = next(execute_vql(vql))
        if result["cmd"] == "select_cmd":
            self.columns = result.get("columns", None)
            self.selection = result.get("source", "variants")
            self.filters = result.get("filter", None)



    def items(self, limit=20, offset=0):
        """Execute SQL query and return variants as a list

        .. note:: Used:
            - as dict of variants in chartquerywidget.py
            - as tuples of variants in viewquerywidget.py

        :param limit: SQL LIMIT for pagination
        :param offset: SQL OFFSET for pagination
        :return: Generator of variants as sqlite3.Row objects.
            A Row instance serves as a highly optimized row_factory for
            Connection objects. It tries to mimic a tuple in most of its features.

            It supports mapping access by column name and index, iteration,
            representation, equality testing and len().
        :rtype: <generator <sqlite3.Row>>

        :Example:

            for row in query.items():
        ...     print(tuple(row))
        (324, "chr2", "24234", "A", "T", ...)
        ...     print(dict(row))
        {"rowid":23423, "chr":"chr2", "pos":4234, "ref":"A", "alt": "T", ...}

        """
        self.conn.row_factory = sqlite3.Row
        sql = self.sql(limit, offset)
        LOGGER.debug(sql)

        for variant in self.conn.execute(sql):
            yield list(dict(variant).values())

    def trees(self, grouped = True, limit=20, offset=0):
        """ Execute Sql Query and returns variants as Tree

        This methods  works only 'group_by' defined and it merge groups results as a tree.
        It usually works with group_by = [chr,pos,ref,alt] when there are several annotations per variants

        Args:
            grouped(bool): Grouped variant by chr,pos,ref,alt. If it is False,  output will be same than self.items()
            limit(int): Maximum number of variants to display per page
            offset(int): Page number

        Examples:
            This is an output with two variants and the correspondant tree. 
            The first variant contains 2 annotations and the second 3 annotations

            [
                [(chr1,2434,A,T, transcriptA),(chr1,2434,A,T, transcriptB),(chr1,2434,A,T, transcriptC)],
                [(chr1,9999,C,T, transcriptA),(chr1,9999,C,T, transcriptB),(chr1,9999,C,T, transcriptC),(chr1,9999,C,T, transcriptD]
            ]
        
            ├── chr1,2434,A,T, transcriptA  # Cannonical transcripts
            │   ├── chr1,2434,A,T, transcriptB
            │   ├── chr1,2434,A,T, transcriptC
            ├── chr1,9999,C,T, transcriptA # Cannonical transcripts
            │   ├── chr1,9999,C,T, transcriptB
            │   ├── chr1,9999,C,T, transcriptC
            │   ├── chr1,9999,C,T, transcriptD



        """
        self.conn.row_factory = sqlite3.Row
    
        
        query = self.build_sql(
            self.columns, 
            self.filters, 
            self.selection,
            self.order_by, 
            self.order_desc,
            grouped, # Grouped 
            limit, offset)

        LOGGER.debug(query)

        for variant in self.conn.execute(query):
            if grouped:
            # Return child count, rows with last ( which is children)
                yield variant["children"], list(dict(variant).values())[:-1]
            else:
                yield 0, list(dict(variant).values())

            
            # if grouped:
            #     ann_filter = {"AND": [{"field": "annotations.variant_id", "operator": "=", "value": variant_id}]}
            #     sub_query = self.build_sql(self.columns,ann_filter,self.selection, limit = None)
            #     for sub_item in self.conn.execute(sub_query):
            #         items.append(list(dict(sub_item).values()))
            # else:
            #items.append(list(dict(variant).values()))    
            #yield items
            
    def children(self, variant_id):
        """ Return children annotations """ 

        self.conn.row_factory = sqlite3.Row
        ann_filter = {"AND": [{"field": "annotations.variant_id", "operator": "=", "value": variant_id}]}
        sub_query = self.build_sql(self.columns,ann_filter,self.selection, limit = None)
        for variant in self.conn.execute(sub_query):
            yield list(dict(variant).values())
        
            

    def count(self, grouped = False):
        """Wrapped function with a memoizing callable that saves up to the
        maxsize most recent calls.

        .. note:: The LRU feature performs best when maxsize is a power-of-two.

        .. note:: The COUNT() aggregation function is expensive on partially
            indexed tables (because dynamically built) for large dataset
            and it seems difficult to predict which fields will be requested
            by the user.
        """

        query = self.sql(grouped = grouped, limit = None)
        print("grouped", grouped, query)

        #Trick to accelerate UI refresh on basic queries
        # if self.selection == "variants" and not self.filters:
        #     return self.conn.execute(
        #         "SELECT MAX(variants.id) as count FROM variants"
        #     ).fetchone()[0]

        return self.conn.execute(
            f"SELECT COUNT(*) as count FROM ({query})"
        ).fetchone()[0]

    @lru_cache(maxsize=128)
    def cache_count(self):
        """ Return lru_cache from self.count 
        """
        return self.count()

    def save(self, name):
        """Save Variant Query into a new selection

        This methods will get all variant.id extracted from self.sql() 
        and insert them into select_has_variant table 

        Args:
            name (str): Selection name

        Return:
            sql index of selection
        """

        cursor = self.conn.cursor()
        count = self.count() # Get count .. Can take a while 

        sql_query = self.build_sql(
            columns = [],
            filters = self.filters,
            selection = self.selection,
            limit = None)

        LOGGER.debug(sql_query)

        # Create selection
        selection_id = insert_selection(cursor,sql_query, name=name, count=count)

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
  
        q = f"""
        INSERT INTO selection_has_variant
        SELECT DISTINCT id, {selection_id} FROM ({sql_query})
        """

        LOGGER.debug(q)

        cursor.execute(q)

        # # REBUILD INDEXES
        # # For joints between selections and variants tables
        create_selection_has_variant_indexes(cursor)

        self.conn.commit()
        if cursor.rowcount:
            return cursor.lastrowid
        return None


    
        
    def __repr__(self):
        return f"""
        columns : {self.columns}
        filter: {self._filters_to_sql(self.filters)}
        selection: {self.selection}
        """



class Selection:
    """Binding object over selection which allows to do set operations on variants
    associated to it

    Attributes:
        - cls.conn: Class attribute for sqlite3 connection.
        - self.query: SQL query ready to be used in set operations.
        - self.mode: Define the way variants are compared to each other.
            - "variant" (default): chr,pos,ref,alt = variant.id
            - "site": chr,pos
        ..seealso:: from_selection_id()
    """

    # Class attribute, shared accross all instances
    conn = None

    def __init__(self, sql_query=None, mode="variant"):
        """Create a new selection object"""
        self.sql_query = sql_query
        # Define the way variants are compared
        self.mode = mode

    def __add__(self, other):
        sql_query = union_variants(self.sql_query, other.sql_query, mode=self.mode)
        return Selection(sql_query, self.mode)

    def __and__(self, other):
        sql_query = intersect_variants(self.sql_query, other.sql_query, mode=self.mode)
        return Selection(sql_query, self.mode)

    def __sub__(self, other):
        sql_query = subtract_variants(self.sql_query, other.sql_query, mode=self.mode)
        return Selection(sql_query, self.mode)

    def __repr__(self):
        return "<Selection>: " + self.sql_query

    def save(self, name):
        """Create the new selection in the database"""
        return create_selection_from_sql(
            Selection.conn, self.sql_query, name, from_selection=True
        )

    @classmethod
    def from_selection_id(cls, selection_id, mode="variant"):
        """Get new Selection object based on a sql query that defines it

        .. note:: Called from the UI. It is here that 'mode' is selected.

        :param selection_id: The id of the selection for which the object will be
            based.
        :key mode: Modifies the definition of the unicity of a variant.
            (optional: "variant" | "site"),(default: "variant").
            - variant: (chr, pos, ref, alt) is the primary key so we query only
            'selection_has_variant' for 'variant_id' field.
            - site: (chr, pos) modifies the default definition of the unicity
            of a variant.
            => joint on 'variants' table is mandatory here.
        :type selection_id: <int>
        :type mode: <str>
        :return: A new Selection object.
        :rtype: <Selection>
        """
        if selection_id == 1:
            # Get ids from the default selection
            sql_query = """SELECT id as variant_id FROM variants"""
        else:
            # A variant is defined as chr,pos,ref,alt
            # which is the primary key (unique)
            # So these columns are synonyms of 'variants.id' for the table 'variants'
            # or 'variant_id' for 'selection_has_variant' table.
            # No further joints are required here.
            sql_query = f"""SELECT variant_id
            FROM selection_has_variant sv
             WHERE sv.selection_id = {selection_id}"""

        return cls(sql_query, mode=mode)
