import sqlite3


class Selection(object):
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.cursor = self.conn.cursor()

    def create(self):
        self.cursor.execute(
            """
        CREATE TABLE selections
        (name text, count text NULL, query text NULL )
        """
        )

        self.cursor.execute(
            """
        CREATE TABLE selection_has_variant
         (variant_id integer, selection_id integer)
         """
        )

        self.conn.commit()

    def insert(self, data: dict):

        data.setdefault("name", "no_name")
        data.setdefault("count", 0)
        data.setdefault("query", "")

        self.cursor.execute(
            """
            INSERT INTO selections VALUES (:name,:count,:query)
            """,
            data,
        )
        self.conn.commit()


class Field(object):
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.cursor = self.conn.cursor()

    def create(self):
        self.cursor.execute(
            """
                CREATE TABLE fields
                 (name text, category text NULL, type text NULL, description text NULL )
                 """
        )
        self.conn.commit()

    def insert(self, data: dict):
        data.setdefault("name", "no_name")
        data.setdefault("category", "")
        data.setdefault("type", "text")
        data.setdefault("description", "")

        self.cursor.execute(
            """
            INSERT INTO selections VALUES (:name,:count,:query)
            """,
            data,
        )
        self.conn.commit()

    def insert_many(self, data: list):
        self.cursor.executemany(
            """
        INSERT INTO fields (name,category,type,description) 
        VALUES (:name,:category,:type, :description)""",
            data,
        )
        self.conn.commit()

    def items(self):
        for row in self.cursor.execute("""SELECT * FROM fields """):
            record = dict()
            record["name"] = row[0]
            record["category"] = row[1]
            record["type"] = row[2]
            record["description"] = row[3]
            yield record


class Variant(object):
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.cursor = self.conn.cursor()

    def create(self, fields):
        #  Create variants tables
        variant_shema = ",".join(
            [f'{field["name"]} {field["type"]} NULL' for field in fields if field["category"] != "sample"]
        )
        self.cursor.execute(f"""CREATE TABLE variants ({variant_shema})""")
        self.conn.commit()

    def insert_many(self, data):
        cols = self.columns()
        # INSERT INTO variants (qcols) VALUES (qplace)
        q_cols = ",".join(cols)
        q_place = ",".join([f":{place}" for place in cols])

        # create dictionnary sampleName: rowId
        samples = dict(
            [
                (record[1], record[0])
                for record in self.conn.execute("""SELECT rowid, name FROM samples""")
            ]
        )

        for row in data:
            self.cursor.execute(
                f"""INSERT INTO variants ({q_cols}) VALUES ({q_place})""", row
            )
            variant_id = self.cursor.lastrowid

            # if row contains sample data, insert ...
            if "samples" in row:
                for sample in row["samples"]:
                    name = sample["name"]
                    gt = sample["gt"]

                    if name in samples.keys():
                        sample_id = samples[name]
                        self.cursor.execute(
                            f"""INSERT INTO sample_has_variant VALUES (?,?,?)""",
                            [sample_id, variant_id, gt],
                        )

        self.conn.commit()

    def columns(self):
        return [
            i[0]
            for i in self.conn.execute("SELECT * FROM variants LIMIT 1").description
        ]


class Sample(object):
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.cursor = self.conn.cursor()

    def create(self):
        self.cursor.execute(
            """
        CREATE TABLE samples
        (name text, phenotype text NULL)
        """
        )

        self.cursor.execute(
            """
        CREATE TABLE sample_has_variant
         (sample_id integer, variant_id integer, gt integer)
         """
        )

        self.conn.commit()

    def insert(self, data: dict):

        data.setdefault("name", "no_name")
        data.setdefault("pheontype", "")

        self.cursor.execute(
            """
            INSERT INTO samples VALUES (:name,:phenotype)
            """,
            data,
        )
        self.conn.commit()

    def list(self):
        return [
            record
            for record in self.cursor.execute(
                """SELECT rowid, name, phenotype FROM samples"""
            )
        ]
