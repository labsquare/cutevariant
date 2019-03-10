import sqlite3
import sys
import collections

def drop_table(conn, table_name):
    c = conn.cursor()
    c.execute(f"DROP TABLE IF EXISTS {table_name}")


def create_project(conn, name, reference):
    cursor = conn.cursor()
    cursor.execute("""CREATE TABLE projects (name text, reference text NULL)""")
    cursor.execute(
        """INSERT INTO projects VALUES (:name,:reference)""",
        {"name": name, "reference": reference},
    )
    conn.commit()


## ================ SELECTION functions =============================


def create_table_selections(conn):
    """ 
    create selection table and selection_has_variant 

    :param conn: sqlite3.connect
    """

    cursor = conn.cursor()
    cursor.execute(
        """CREATE TABLE selections (name text, count INTEGER NULL, query text NULL )"""
    )
    cursor.execute(
        """CREATE TABLE selection_has_variant (variant_id integer, selection_id integer)"""
    )
    conn.commit()


def insert_selection(conn, name="no_name", count=0, query=str()):
    """ 
    insert one selection

    :param conn: sqlite3.connect
     """
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO selections VALUES (:name,:count,:query)""",
        {"name": name, "count": count, "query": query},
    )
    conn.commit()
    return cursor.lastrowid


def create_selection_from_sql(conn, name, query, by="site"):

    #  Create selection
    selection_id = insert_selection(conn, name=name, count=0, query=query)

    # insert into selection_has_variants
    if by == "site":
        q = f"""
        INSERT INTO selection_has_variant 
        SELECT variants.rowid, {selection_id} FROM variants
        INNER JOIN ({query}) query WHERE variants.chr = query.chr AND variants.pos = query.pos
        """

    if by == "variant":
        q = f"""
        INSERT INTO selection_has_variant 
        SELECT variants.rowid, {selection_id} FROM variants 
        INNER JOIN ({query}) as query 
        WHERE variants.chr = query.chr AND variants.pos = query.pos AND variants.ref = query.ref AND variants.alt = query.alt
        """

    cursor = conn.cursor()
    cursor.execute(q)
    conn.commit()

    #  update selection count
    cursor.execute(
        f"""
        UPDATE selections set count = (SELECT COUNT(*) FROM selection_has_variant WHERE selection_id = {selection_id}) WHERE selections.rowid = {selection_id}
        """
    )

    conn.commit()


def get_selections(conn):
    cursor = conn.cursor()
    for row in cursor.execute("""SELECT * FROM selections """):
        record = dict()
        record["name"] = row[0]
        record["count"] = row[1]
        record["query"] = row[2]
        yield record


def intersect_variants(query1, query2, by="site"):

    if by == "site":
        col = "chr,pos"

    if by == "variant":
        col = "chr,pos,ref,alt"

    return f"""
    SELECT {col} FROM ({query1})
    INTERSECT 
    SELECT {col} FROM ({query2})
    """

    return query


def union_variants(query1, query2, by="site"):
    if by == "site":
        col = "chr,pos"

    if by == "variant":
        col = "chr,pos,ref,alt"

    return f"""
    SELECT {col} FROM ({query1})
    UNION
    SELECT {col} FROM ({query2})
    """


def subtract_variants(query1, query2, by="site"):
    if by == "site":
        col = "chr,pos"

    if by == "variant":
        col = "chr,pos,ref,alt"

    return f"""
    SELECT {col} FROM ({query1})
    EXCEPT
    SELECT {col} FROM ({query2})
    """


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


def insert_field(
    conn, name="no_name", category="variants", type="text", description=str()
):
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
        {"name": name, "category": category, "type": type, "description": description},
    )
    conn.commit()
    return cursor.lastrowid


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
        [
            f'{field["name"]} {field["type"]} NULL'
            for field in fields
            if field["category"] != "sample"
        ]
    )
    cursor.execute(f"""CREATE TABLE variants ({variant_shema})""")
    cursor.execute(
        f"""CREATE TABLE sample_has_variant (sample_id INTEGER, variant_id INTEGER, gt INTEGER DEFAULT -1 )"""
    )

    # cursor.execute(f"""CREATE INDEX sample_has_variant_ids ON sample_has_variant (variant_id, sample_id)""")

    conn.commit()


def get_one_variant(conn, id : int):

    variant = {"rowid" : id}

    cols = [i[0] for i in conn.execute("SELECT * FROM variants LIMIT 1").description]
    values = conn.execute(f""" SELECT * FROM variants WHERE rowid = {id}""").fetchone()     
    variant.update(dict(zip(cols,values)))
    return variant

    # cursor = conn.cursor()
    # return cursor.fetchone()




def insert_many_variants(conn, data, total_variant_count=-1, commit_every=200):
    """
    Insert many variant from data into variant table.columns

    :param conn: sqlite3.connect
    :param data: list of variant dictionnary which contains same number of key than fields numbers. 
    :param variant_count: total variant count, to compute progression

    :Example: 

    insert_many_variant(conn, [{chr:"chr1", pos:24234, alt:"A","ref":T }]) 
    insert_many_variant(conn, reader.get_variants())
    
    .. warning:: Using reader, this can take a while
    ... todo:: with large dataset, need to cache import   
    .. seealso:: abstractreader
    """



    cursor = conn.cursor()

    #  Get columns description from variant table
    cols = [i[0] for i in conn.execute("SELECT * FROM variants LIMIT 1").description]

    # build dynamic insert query
    # INSERT INTO variant qcol1, qcol2.... VALUES :qcol1, :qcol2 ....
    q_cols = ",".join(cols)
    q_place = ",".join([f":{place}" for place in cols])

    # get samples with sql rowid
    samples = dict(
        [
            (record[1], record[0])
            for record in conn.execute("""SELECT rowid, name FROM samples""")
        ]
    )

    # Loop over variants
    variant_count = 0  # count variants
    insert_count = (
        0
    )  #  count insertion in sql ( one variant can have multiple insertion depending on annotation)

    for variant in data:

        # use default dict for missing value 
        variant = collections.defaultdict(lambda : "", variant)


        variant_count += 1

        ## Split variant into multiple variant if there are multiple annotation
        variants = []
        if "annotation" in variant:
            for annotation in variant["annotation"]:
                new_variant = dict(variant)
                new_variant.update(annotation)
                del new_variant["annotation"]
                variants.append(new_variant)
        else:
            variants.append(variant)

        for variant_to_insert in variants:

            # Insert current variant
            cursor.execute(
                f"""INSERT INTO variants ({q_cols}) VALUES ({q_place})""",
                variant_to_insert,
            )

            # get variant rowid
            variant_id = cursor.lastrowid
            insert_count += 1

            #  every commit_every = 200 insert, start a commit ! This value can be changed
            if insert_count % commit_every == 0:
                progress = float(variant_count) / total_variant_count * 100.0
                yield progress, f"{variant_count} variant inserted"
                conn.commit()

            # if variant has sample data, insert record into sample_has_variant
            if "samples" in variant:
                for sample in variant["samples"]:
                    name = sample["name"]
                    gt = sample["gt"]

                    if name in samples.keys():
                        sample_id = samples[name]
                        cursor.execute(
                            f"""INSERT INTO sample_has_variant VALUES (?,?,?)""",
                            [sample_id, variant_id, gt],
                        )

    conn.commit()
    #  create index to make sample query faster
    cursor.execute(
        f"""CREATE UNIQUE INDEX idx_sample_has_variant ON sample_has_variant (sample_id,variant_id)"""
    )

    # create selections
    insert_selection(conn, name="all", count=variant_count)

    yield 100, f"{variant_count} variant(s) has been inserted"


## ================ Fields functions =============================


def create_table_samples(conn):
    """
    Create sample table 

    :param conn: sqlite3.connect

    """
    cursor = conn.cursor()
    cursor.execute("""CREATE TABLE samples (name text)""")
    conn.commit()


def insert_sample(conn, name="no_name"):
    """
    Insert one sample in sample table 

    :param conn: sqlite3.connect

    """
    cursor = conn.cursor()
    cursor.execute(""" INSERT INTO samples VALUES (:name) """, {"name": name})

    conn.commit()
    return cursor.lastrowid


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
