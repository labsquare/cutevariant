import sqlite3 



class Selection(object):
    def __init__(self, conn : sqlite3.Connection):
        self.conn = conn
        self.cursor = self.conn.cursor()

    def create(self):
        self.cursor.execute('''
        CREATE TABLE selections
        (name text, count text NULL, query text NULL )
        ''')

        self.cursor.execute('''
        CREATE TABLE selection_has_variant
         (variant_id integer, selection_id integer)
         ''')

        self.conn.commit()

    def insert(self, data : dict):

        data.setdefault("name", "no_name")
        data.setdefault("count", 0)
        data.setdefault("query", "")

        self.cursor.execute('''
            INSERT INTO selections VALUES (:name,:count,:query)
            ''', data)
        self.conn.commit()



class Field(object):
    def __init__(self, conn : sqlite3.Connection):
        self.conn = conn
        self.cursor = self.conn.cursor()

    def create(self):
        self.cursor.execute('''
                CREATE TABLE fields
                 (name text, category text NULL, type text NULL, description text NULL )
                 ''')
        self.conn.commit()

    def insert(self, data: dict):
        data.setdefault("name", "no_name")
        data.setdefault("category", "")
        data.setdefault("type", "text")
        data.setdefault("description", "")

        self.cursor.execute('''
            INSERT INTO selections VALUES (:name,:count,:query)
            ''', data)
        self.conn.commit()


    def insert_many(self, data : list):
        self.cursor.executemany('''
        INSERT INTO fields (name,category,type,description) 
        VALUES (:name,:category,:type, :description)''', data)
        self.conn.commit()


class Variant(object):
    def __init__(self, conn : sqlite3.Connection):
        self.conn = conn 
        self.cursor = self.conn.cursor()

    def create(self, fields):
    # Create variants tables 
        variant_shema = ",".join([f'{field["name"]} {field["type"]} NULL' for field in fields])
        self.cursor.execute(f'''CREATE TABLE variants ({variant_shema})''')
        self.conn.commit()

    def insert_many(self, data):
        cols = self.columns()
        # INSERT INTO variants (qcols) VALUES (qplace)
        q_cols  = ','.join(cols) 
        q_place = ','.join([f':{place}' for place in cols])
        
        self.cursor.executemany(f'''INSERT INTO variants ({q_cols}) VALUES ({q_place})''', data)
        self.conn.commit()

    def columns(self):
        return [i[0] for i in self.conn.execute("SELECT * FROM variants LIMIT 1").description]