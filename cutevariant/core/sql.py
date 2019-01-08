import sqlite3




def drop_table(conn, table_name):
    c = conn.cursor()
    c.execute(f"DROP TABLE IF EXISTS {table_name}")






## ================ SELECTION functions =============================

def create_table_selections(conn):
    """ 
    create selection table and selection_has_variant 

    :param conn: sqlite3.connect
    """ 

    cursor = conn.cursor()
    cursor.execute("""CREATE TABLE selections (name text, count text NULL, query text NULL )""")
    cursor.execute("""CREATE TABLE selection_has_variant (variant_id integer, selection_id integer)""")
    conn.commit()

def insert_selection(conn, name = "no_name", count=0, query=str()):
    """ 
    insert one selection

    :param conn: sqlite3.connect
     """ 
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO selections VALUES (:name,:count,:query)""",
        {"name": name, "count": count, "query": query}
        )
    conn.commit()


## ================ Fields functions =============================

def create_table_fields(conn):
    """ 
    create field table 

    :param conn: sqlite3.connect

    """ 
    cursor = conn.cursor()
    cursor.execute(
        """CREATE TABLE fields
        (name text, category text NULL, type text NULL, description text NULL )
        """
    )
    conn.commit()


def insert_field(conn, name = "no_name", category ="variants", type = "text", description = str()):
    """ 
    insert one field 

    :param conn: sqlite3.connect
    :param name: field name
    :param category: category field name. The default is "variants". Don't use sample as category name
    :param type: sqlite type which can be : integer, real, text
    """ 
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO fields VALUES (:name,:category, :type, :description)
        """,
        {"name": name, "category": category, "type": type, "description" : description})
    conn.commit()


def insert_many_fields(conn, data: list):
    """ 
    insert many fields using one commit 

    :param conn: sqlite3.connect
    :param data: list of field dictionnary

    :Exemple: 

    insert_many_field(conn, [{name:"sacha", category:"variant", count: 0, description="a description"}])
    insert_many_field(conn, reader.get_fields())

    .. seealso:: insert_field, abstractreader

    """
    cursor = conn.cursor()
    cursor.executemany(
        """
        INSERT INTO fields (name,category,type,description) 
        VALUES (:name,:category,:type, :description)
        """,
        data,
    )
    conn.commit()


def get_fields(conn):
    """ 
    return fields as list of dictionnary 

    :param conn: sqlite3.connect
    :return: list of dictionnary 

    .. seealso:: insert_many_field

    """ 
    cursor = conn.cursor()

    for row in cursor.execute("""SELECT * FROM fields """):
        record = dict()
        record["name"] = row[0]
        record["category"] = row[1]
        record["type"] = row[2]
        record["description"] = row[3]
        yield record

## ================ Fields functions =============================


def create_table_variants(conn, fields):
    """
    Create variant table which contains dynamics fields 

    :param conn: sqlite3.connect
    :param fields: list of field dictionnary. 
    
    :Example: 
    
    fields = get_fields()
    create_variant_table(conn, fields)

    .. seealso:: get_fields

    """
    cursor = conn.cursor()

    variant_shema = ",".join(
        [f'{field["name"]} {field["type"]} NULL' for field in fields if field["category"] != "sample"]
    )
    cursor.execute(f"""CREATE TABLE variants ({variant_shema})""")
    cursor.execute(f"""CREATE TABLE sample_has_variant (sample_id INTEGER, variant_id, gt INTEGER DEFAULT -1 )""")
    
    conn.commit()



def insert_many_variants(conn, data):
    """
    Insert many variant from data into variant table.columns

    :param conn: sqlite3.connect
    :param data: list of variant dictionnary which contains same number of key than fields numbers. 

    :Example: 

    insert_many_variant(conn, [{chr:"chr1", pos:24234, alt:"A","ref":T }]) 
    insert_many_variant(conn, reader.get_variants())
    
    .. warning:: Using reader, this can take a while
    ... todo:: with large dataset, need to cache import   
    .. seealso:: abstractreader
    """

    cursor = conn.cursor()

    # Get columns description from variant table 
    cols =   [i[0] for i in conn.execute("SELECT * FROM variants LIMIT 1").description ]

    # build dynamic insert query 
    # INSERT INTO variant qcol1, qcol2.... VALUES :qcol1, :qcol2 ....
    q_cols  = ",".join(cols)
    q_place = ",".join([f":{place}" for place in cols])

    # get samples with sql rowid 
    samples = dict(
        [
            (record[1], record[0])
            for record in conn.execute("""SELECT rowid, name FROM samples""")
        ]
    )

    # Loop over variants 
    for variant in data:
        # Insert current variant 
        cursor.execute(
            f"""INSERT INTO variants ({q_cols}) VALUES ({q_place})""", variant
        )

        # get variant rowid 
        variant_id = cursor.lastrowid

        # if variant has sample data, insert record into sample_has_variant 
        if "samples" in variant:
            for sample in variant["samples"]:
                name = sample["name"]
                gt   = sample["gt"]

                if name in samples.keys():
                    sample_id = samples[name]
                    cursor.execute(
                        f"""INSERT INTO sample_has_variant VALUES (?,?,?)""",
                        [sample_id, variant_id, gt],
                    )

    conn.commit()

    # create index to make sample query faster 
    cursor.execute(f"""CREATE UNIQUE INDEX idx_sample_has_variant ON sample_has_variant (sample_id,variant_id)""")


## ================ Fields functions =============================

def create_table_samples(conn):
    """
    Create sample table 

    :param conn: sqlite3.connect

    """
    cursor = conn.cursor()
    cursor.execute("""CREATE TABLE samples (name text)""")
    conn.commit()


def insert_sample(conn, name = "no_name"):
    """
    Insert one sample in sample table 

    :param conn: sqlite3.connect

    """
    cursor = conn.cursor()
    cursor.execute(""" INSERT INTO samples VALUES (:name) """, {"name": name})
    
    conn.commit()


def get_samples(conn):
    """"
    Get samples from sample table 

    :param con: sqlite3.conn 
    :return sample list
    """
    cursor = conn.cursor()
    record = dict()
    for row in cursor.execute("""SELECT name FROM samples"""):
        record["name"] = row[0]
        yield record

