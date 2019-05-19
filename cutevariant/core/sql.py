"""Module bringing together all the SQL related functions.

- Misc functions
- Selections functions
- Fields functions
- Operations on sets of variants
- Annotations functions
- Variants functions
- Samples functions
"""

# Standard imports
import sqlite3
import sys
from collections import defaultdict
from pkg_resources import parse_version

# Custom imports
import cutevariant.commons as cm

LOGGER = cm.logger()


## ================ Misc functions =============================================


def get_sql_connexion(filepath):
    """Open a SQLite database and return the connexion object"""
    connexion = sqlite3.connect(filepath)
    # Activate Foreign keys
    connexion.execute("PRAGMA foreign_keys = ON")
    connexion.row_factory = sqlite3.Row
    foreign_keys_status = connexion.execute("PRAGMA foreign_keys").fetchone()[0]
    LOGGER.debug("get_sql_connexion:: foreign_keys state: %s", foreign_keys_status)
    assert foreign_keys_status == 1, "Foreign keys can't be activated :("
    return connexion


def drop_table(conn, table_name):
    """Drop the given table"""
    cursor = conn.cursor()
    cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
    conn.commit()


def create_project(conn, name: str, reference: str):
    """Create the table "projects" and insert project name and reference genome

    :param conn: sqlite3.connect
    :param name: Project's name
    :param reference: Reference genome
    """
    cursor = conn.cursor()
    cursor.execute(
        """CREATE TABLE projects (id INTEGER PRIMARY KEY, name TEXT, reference TEXT)"""
    )
    cursor.execute(
        """INSERT INTO projects (name, reference) VALUES (?, ?)""", (name, reference)
    )
    conn.commit()


def get_columns(conn, table_name):
    """Return the list of columns for the given table

    .. note:: used by async_insert_many_variants()
        to build queries with placeholders

    :param conn: sqlite3.connect
    :param table_name: Table for which columns will be returned.
    """
    # Get columns description from table_info
    # ((0, 'chr', 'str', 0, None, 1), ...
    return [
        c[1] for c in conn.execute(f"pragma table_info({table_name})") if c[1] != "id"
    ]


def create_indexes(conn):
    """Create extra indexes on tables

    .. note:: This function must be called after batch insertions.
    .. note:: You should use this function instead of individual functions.
    """
    create_variants_indexes(conn)
    create_selections_indexes(conn)

    try:
        # Some databases have not annotations table
        create_annotations_indexes(conn)
    except sqlite3.OperationalError as e:
        LOGGER.debug("create_indexes:: sqlite3.%s: %s", e.__class__.__name__, str(e))


## ================ Selections functions =======================================


def create_table_selections(conn):
    """Create the table "selections" and association table "selection_has_variant"

    This table stores the queries saved by the user:
        - name: name of the set of variants
        - count: number of variants concerned by this set
        - query: the SQL query which generated the set

    :param conn: sqlite3.connect
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


def create_selections_indexes(conn):
    """Create indexes on the "selections" table

    .. note:: This function should be called after batch insertions.

    .. note:: This function ensures the unicity of selections names.
    """
    conn.execute("""CREATE UNIQUE INDEX idx_selections ON selections (name)""")


def create_selection_has_variant_indexes(conn):
    """Create indexes on "selection_has_variant" table

    .. note:: This function is called by:
        - create_selections_indexes
        - insert_selection to rebuild index
    """
    # For joints between selections and variants tables
    conn.execute(
        """CREATE INDEX idx_selection_has_variant ON selection_has_variant (selection_id)"""
    )


def insert_selection(conn, query: str, name="no_name", count=0):
    """Insert one selection record

    TODO: retirer le group by inutile

    .. warning:: This function does a commit !

    :param conn: sqlite3 connection OR cursor
        If connection: commit is made.
        If cursor: commit is not made.
    :param name: name of the selection
    :param count: precompute variant count
    :param query: Sql variant query selection
    :type conn: <sqlite3.Connection> or <sqlite3.Cursor>
    :return: rowid of the new selection inserted.
    :rtype: <int>

    .. seealso:: create_selection_from_sql
    """
    # conn can be a cursor or a connection here...
    cursor = conn.cursor() if isinstance(conn, sqlite3.Connection) else conn

    cursor.execute(
        """INSERT INTO selections (name, count, query) VALUES (?,?,?)""",
        (name, count, query),
    )
    if isinstance(conn, sqlite3.Connection):
        # Commit only if connection is given. => avoid not consistent DB
        conn.commit()
    return cursor.lastrowid


def create_selection_from_sql(
    conn, query: str, name: str, count=None, from_selection=False
):
    """Create a selection record from sql variant query

    :param name : name of the selection
    :param query: sql variant query
    :param by: can be : 'site' for (chr,pos)  or 'variant' for (chr,pos,ref,alt)
    :return: The id of the new selection. None in case of error.
    :rtype: <int> or None
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


def get_selections(conn):
    """Get selections in "selections" table

    :return: Generator of dictionnaries with as many keys as there are columns
        in the table.
        Dictionnary of all attributes of the table.
            :Example: {"id": ..., "name": ..., "count": ..., "query": ...}
    :rtype: <generator <dict>>
    """
    conn.row_factory = sqlite3.Row
    return (dict(data) for data in conn.execute("""SELECT * FROM selections"""))


def delete_selection(conn, selection_id: int):
    """Delete the selection with the given id in the "selections" table

    :return: Number of rows deleted
    :rtype: <int>
    """
    # ON CASCADE deletion
    cursor = conn.cursor()
    cursor.execute("DELETE FROM selections WHERE rowid = ?", (selection_id,))
    conn.commit()
    return cursor.rowcount


def edit_selection(conn, selection: dict):
    """Update the name and count of a selection with the given id

    :return: Number of rows deleted
    :rtype: <int>
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
    """Get the variants obtained by the intersection of 2 queries"""
    return f"""{query1} INTERSECT {query2}"""


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

    # Association table: do not use useless rowid column
    cursor.execute(
        """CREATE TABLE sample_has_variant (
        sample_id INTEGER NOT NULL,
        variant_id INTEGER NOT NULL,
        gt INTEGER DEFAULT -1,
        PRIMARY KEY (sample_id, variant_id),
        FOREIGN KEY (sample_id) REFERENCES samples (id)
          ON DELETE CASCADE
          ON UPDATE NO ACTION
        ) WITHOUT ROWID"""
    )
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
        """Build a tuple of columns and formatted placeholders for INSERT queries
        """
        # Get columns description from the given table
        cols = get_columns(conn, table_name)
        # Build dynamic insert query
        # INSERT INTO variant qcol1, qcol2.... VALUES :qcol1, :qcol2 ....
        tb_cols = ",".join([f"`{col}`" for col in cols])
        tb_places = ",".join([f":{place}" for place in cols])
        return tb_cols, tb_places

    # TODO: Can we avoid this step ? This function should receive columns names
    # because all the tables were created before...
    # Build placeholders
    var_cols, var_places = build_columns_and_placeholders("variants")
    ann_cols, ann_places = build_columns_and_placeholders("annotations")

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
        LOGGER.debug(variant_insert_query)
        print(variant_insert_query)

        cursor.execute(variant_insert_query, defaultdict(str, variant))

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
            temp_ann_places = ann_places.replace(":variant_id,", "")
            cursor.executemany(
                f"""INSERT INTO annotations ({ann_cols})
                VALUES ({variant_id}, {temp_ann_places})""",
                variant["annotations"],
            )

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
            g = (
                (samples_id_mapping[sample["name"]], sample["gt"])
                for sample in variant["samples"]
                if sample["name"] in samples_names
            )
            cursor.executemany(
                f"""INSERT INTO sample_has_variant VALUES (?,{variant_id},?)""", g
            )

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


def create_table_samples(conn):
    """Create samples table

    :param conn: sqlite3.connect
    """
    cursor = conn.cursor()
    # sample_id is an alias on internal autoincremented 'rowid'
    cursor.execute(
        """CREATE TABLE samples (
        id INTEGER PRIMARY KEY ASC,
        name TEXT)"""
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
