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
    cursor.execute("""CREATE TABLE projects (name TEXT, reference TEXT)""")
    cursor.execute(
        """INSERT INTO projects VALUES (?, ?)""",
        (name, reference),
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
    return [c[1] for c in conn.execute(f"pragma table_info({table_name})")]


## ================ Selections functions =======================================


def create_table_selections(conn):
    """Create the table "selections" and association table "selection_has_variant"

    This table stores the queries saved by the user.

    :param conn: sqlite3.connect
    """
    cursor = conn.cursor()
    # selection_id is an alias on internal autoincremented 'rowid'
    cursor.execute(
        """CREATE TABLE selections (
        selection_id INTEGER PRIMARY KEY ASC,
        name TEXT, count INTEGER, query TEXT
        )"""
    )

    # Association table: do not use useless rowid column
    cursor.execute(
        """CREATE TABLE selection_has_variant (
        variant_id INTEGER NOT NULL,
        selection_id INTEGER NOT NULL,
        PRIMARY KEY (variant_id, selection_id),
        FOREIGN KEY (selection_id) REFERENCES selections (selection_id)
          ON DELETE CASCADE
          ON UPDATE NO ACTION
        ) WITHOUT ROWID"""
    )
    conn.commit()


def insert_selection(conn, query=str(), name="no_name", count=0):
    """Insert one selection record (NOT USED)

    .. warning:: This function does a commit !

    :param conn: sqlite3.connect
    :param name: name of the selection
    :param count: precompute variant count
    :param query: Sql variant query selection
    :return: rowid of the new selection inserted.
    :rtype: <int>

    .. seealso:: create_selection_from_sql
    """
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO selections (name, count, query) VALUES (?,?,?)""",
        (name, count, query)
    )
    # TODO: get cursor as argument, because later insertions may crash
    # and leave the database not consistent with an orphan selection.
    conn.commit()
    return cursor.lastrowid


def create_selection_from_sql(conn,query, name, by="site", count=None):
    """Create a selection record from sql variant query

    :param name : name of the selection
    :param query: sql variant query
    :param by: can be : 'site' for (chr,pos)  or 'variant' for (chr,pos,ref,alt)
    """
    assert by in ("site", "variant")

    cursor = conn.cursor()

    # Compute query count
    # TODO : this can take a while .... need to compute only one from elsewhere
    if count is None:
        count = cursor.execute(f"SELECT COUNT(*) FROM ({query})").fetchone()[0]

    # Create selection
    selection_id = insert_selection(conn, name=name, count=count, query=query)

    # Insert into selection_has_variant table
    # PS: We use DISTINCT keyword to statisfy the unicity constraint on
    # (variant_id, selection_id) of "selection_has_variant" table.
    if by == "site":
        q = f"""
        INSERT INTO selection_has_variant
        SELECT DISTINCT variants.rowid, {selection_id} FROM variants
        INNER JOIN ({query}) query
            ON variants.chr = query.chr
            AND variants.pos = query.pos
        """

    if by == "variant":
        q = f"""
        INSERT INTO selection_has_variant
        SELECT DISTINCT variants.rowid, {selection_id} FROM variants
        INNER JOIN ({query}) as query
            ON variants.chr = query.chr
            AND variants.pos = query.pos
            AND variants.ref = query.ref
            AND variants.alt = query.alt
        """

    cursor.execute(q)
    conn.commit()


def get_selections(conn):
    """Get selections in "selections" table

    :return: Dictionnary of all attributes of the table.
        :Example: {"name": ..., "count": ..., "query": ...}
    :rtype: <dict>
    """
    conn.row_factory = sqlite3.Row
    return (dict(data) for data in conn.execute("""SELECT * FROM selections"""))


## ================ Operations on sets of variants =============================


def get_query_columns(by):
    """Handy func to get columns to be queried according to the group by argument

    .. note:: Used by intersect_variants, union_variants, subtract_variants
        in order to avoid code duplication.
    """
    if by == "site":
        return "chr,pos"

    if by == "variant":
        return "chr,pos,ref,alt"

    raise NotImplementedError


def intersect_variants(query1, query2, by="site"):
    """Get the variants obtained by the intersection of 2 queries"""
    columns = get_query_columns(by)
    return f"""
    SELECT {columns} FROM ({query1})
    INTERSECT
    SELECT {columns} FROM ({query2})
    """


def union_variants(query1, query2, by="site"):
    """Get the variants obtained by the union of 2 queries"""
    columns = get_query_columns(by)
    return f"""
    SELECT {columns} FROM ({query1})
    UNION
    SELECT {columns} FROM ({query2})
    """


def subtract_variants(query1, query2, by="site"):
    """Get the variants obtained by the difference of 2 queries"""
    columns = get_query_columns(by)
    return f"""
    SELECT {columns} FROM ({query1})
    EXCEPT
    SELECT {columns} FROM ({query2})
    """


## ================ Fields functions ===========================================


def create_table_fields(conn):
    """Create the table "fields"

    .. todo:: What is this table supposed to store?

    :param conn: sqlite3.connect
    """
    cursor = conn.cursor()
    cursor.execute(
        """CREATE TABLE fields
        (name TEXT, category TEXT, type TEXT, description TEXT)
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
    :key description: TODO
    :return: Last row id
    :rtype: <int>
    """
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO fields VALUES (?, ?, ?, ?)
        """,
        (name, category, type, description)
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

    :param conn: sqlite3.connect
    :return: Generator of dictionnaries

    .. seealso:: insert_many_fields
    .. todo:: Should this function retun a dict??
        Later, the dict is almost useless and it is very repetitive...
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
    # TODO: primary MUST NOT have NULL fields !!
    schema = ",".join(
        [
            f'{field["name"]} {field["type"]} NULL'
            for field in fields
        ]
    )

    if not schema:
        LOGGER.debug("create_table_annotations:: No annotation fields")
        return

    cursor = conn.cursor()
    cursor.execute(f"""CREATE TABLE annotations (variant_id INTEGER, {schema})""")
    # TODO: make indexes after insertions...
    cursor.execute(f"""CREATE INDEX idx_annotations ON annotations (variant_id)""")
    conn.commit()


## ================ Variants functions =========================================


def create_table_variants(conn, fields):
    """Create "variants" table which contains dynamics fields

    :param conn: sqlite3.connect
    :param fields: list of field dictionnary.

    :Example:

        fields = get_fields()
        create_table_variants(conn, fields)

    .. seealso:: get_fields

    """
    cursor = conn.cursor()

    # Primary key MUST NOT have NULL fields !
    # PRIMARY KEY should always imply NOT NULL.
    # Unfortunately, due to a bug in some early versions, this is not the case in SQLite.
    # For the purposes of UNIQUE constraints, NULL values are considered distinct
    # from all other values, including other NULLs.
    schema = ",".join(
        [
            f'{field["name"]} {field["type"]} {field.get("constraint", "")}'
            for field in fields if field["name"]
        ]
    )

    LOGGER.debug("create_table_variants:: schema: %s", schema)
    # Unicity constraint or NOT NULL fields
    # NOTE: specify the constraint in CREATE TABLE generates a lighter DB than
    # a separated index... Don't know why.
    cursor.execute(f"""CREATE TABLE variants ({schema},
        UNIQUE (chr,pos,ref,alt))""")
    # cursor.execute(f"""CREATE UNIQUE INDEX idx_variants_unicity ON variants (chr,pos,ref,alt)""")
    # Association table: do not use useless rowid column
    cursor.execute(f"""CREATE TABLE sample_has_variant (
        sample_id INTEGER NOT NULL,
        variant_id INTEGER NOT NULL,
        gt INTEGER DEFAULT -1,
        PRIMARY KEY (sample_id, variant_id),
        FOREIGN KEY (sample_id) REFERENCES samples (sample_id)
          ON DELETE CASCADE
          ON UPDATE NO ACTION
        ) WITHOUT ROWID""")
    # TODO: make indexes after insertions...
    cursor.execute(f"""CREATE UNIQUE INDEX idx_sample_has_variant ON sample_has_variant (sample_id,variant_id)""")
    conn.commit()


def get_one_variant(conn, id: int):
    """Get the variant with the given id"""
    print("FACTORY:", conn.row_factory)
    # Use row_factory here
    conn.row_factory = sqlite3.Row
    # Cast sqlite3.Row object to dict because later, we use items() method.
    return dict(
        conn.execute(f"""SELECT * FROM variants WHERE rowid = {id}""").fetchone()
    )


def get_variants_count(conn):
    """Get the number of variants in the "variants" table"""
    return conn.execute(f"""SELECT COUNT(*) FROM variants""").fetchone()[0]


def async_insert_many_variants(conn, data, total_variant_count=None, yield_every=200):
    """Insert many variants from data into variants table

    :param conn: sqlite3.connect
    :param data: list of variant dictionnary which contains same number of key than fields numbers.
    :param variant_count: total variant count, to compute progression

    :Example:

        insert_many_variant(conn, [{chr:"chr1", pos:24234, alt:"A","ref":T }])
        insert_many_variant(conn, reader.get_variants())

    .. warning:: Using reader, this can take a while
    .. todo:: with large dataset, need to cache import
    .. seealso:: abstractreader


    INSERT IGNORE avoids error

    Upon insertion of a duplicate key where the column must contain a PRIMARY KEY or UNIQUE constraint
    Upon insertion of NULL value where the column has a NOT NULL constraint.


    """
    print("FACTORY:", conn.row_factory)

    # TODO: Can we avoid this step ? This function should receive columns names
    # because all the tables were created before...

    def build_columns_and_placeholders(table_name):
        """Build a tuple of columns and formatted placeholders for INSERT queries
        """
        # Get columns description from the given table
        cols = get_columns(conn, table_name)
        # Build dynamic insert query
        # INSERT INTO variant qcol1, qcol2.... VALUES :qcol1, :qcol2 ....
        tb_cols = ",".join(cols)
        tb_places = ",".join([f":{place}" for place in cols])
        return tb_cols, tb_places

    # Build placeholders
    var_cols, var_places = build_columns_and_placeholders("variants")
    ann_cols, ann_places = build_columns_and_placeholders("annotations")


    # Get samples with samples names as keys and sqlite rowid as values
    # => used as a mapping for samples ids
    samples_id_mapping = {name: rowid for name, rowid
               in conn.execute("""SELECT name, rowid FROM samples""")}
    samples_names = samples_id_mapping.keys()
    # print("SAMPLES:", samples_id_mapping)


    cursor = conn.cursor()

    # Loop over variants
    for variant_count, variant in enumerate(data, 1):

        # Insert current variant
        # TODO: handle errors here... is the lastrowid updated if duplication ignored ???
        if parse_version(sqlite3.sqlite_version) < parse_version("3.24.0"):
            LOGGER.warning("async_insert_many_variants:: Old SQLite version: %s"
                           " - Fallback to ignore errors!",
                           sqlite3.sqlite_version)
            # Use default dict to handle missing values
            # /!\ This syntax is SQLite specific
            cursor.execute(
                f"""INSERT OR IGNORE INTO variants ({var_cols})
                VALUES ({var_places})""",
                defaultdict(str,variant))
        else:
            # Use default dict to handle missing values
            # Handle conflicts on the primary key
            cursor.execute(
                f"""INSERT INTO variants ({var_cols})
                VALUES ({var_places})
                ON CONFLICT (chr,pos,ref,alt) DO NOTHING""",
                defaultdict(str,variant))

        # Get variant rowid
        variant_id = cursor.lastrowid

        # If variant has annotation data, insert record into "annotations" table
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
                variant["annotations"]
            )

        # If variant has sample data, insert record into "sample_has_variant" table
        if "samples" in variant:
            # print("VAR samples:", variant["samples"])
            # [{'name': 'NORMAL', 'gt': 1, 'AD': '64,0', 'AF': 0.0, ...}]
            # Insertion only if the current sample name is in samples_names
            # (authorized sample names already in the database)
            # TODO: is this test usefull since samples that are in the database
            # have been inserted from the same source file (or it is not the case ?) ?
            # Retrieve the id of the sample to build the association in
            # "sample_has_variant" table carrying the data "gt" (genotype)
            g = ((samples_id_mapping[sample["name"]], sample["gt"])
                 for sample in variant["samples"]
                 if sample["name"] in samples_names)
            cursor.executemany(
                f"""INSERT INTO sample_has_variant VALUES (?,{variant_id},?)""",
                g
            )


        # Yield progression
        if variant_count % yield_every == 0:
            if total_variant_count:
                progress = variant_count / total_variant_count * 100
            else:
                progress = 0

            yield progress, f"{variant_count} variants inserted."

    conn.commit()

    # Create indexes
    # yield 90, "Create indexes"
    # TODO: ....


    # create selections
    # insert_selection(conn, name="all", count=variant_count)

    yield 100, f"{variant_count} variant(s) has been inserted"


def insert_many_variants(conn, data, **kwargs):
    for _,_ in async_insert_many_variants(conn, data, kwargs):
        pass


## ================ Samples functions ==========================================


def create_table_samples(conn):
    """Create samples table

    :param conn: sqlite3.connect
    """
    cursor = conn.cursor()
    # sample_id is an alias on internal autoincremented 'rowid'
    cursor.execute("""CREATE TABLE samples (
        sample_id INTEGER PRIMARY KEY ASC,
        name TEXT)""")
    conn.commit()


def insert_sample(conn, name="no_name"):
    """Insert one sample in samples table

    :param conn: sqlite3.connect
    :return: Last row id
    :rtype: <int>
    """
    cursor = conn.cursor()
    cursor.execute("""INSERT INTO samples VALUES (?)""", [name])
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
        """INSERT INTO samples (name) VALUES (?)""",
        ((sample,) for sample in samples)
    )
    conn.commit()


def get_samples(conn):
    """"Get samples from sample table

    :param con: sqlite3.conn
    :return sample list
    """
    conn.row_factory = sqlite3.Row
    return (dict(data) for data in conn.execute("""SELECT name FROM samples"""))
