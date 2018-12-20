import os
import csv
import sqlite3
from .readerfactory import ReaderFactory
from .model import Selection, Field, Variant

def import_file(filename, dbpath):

    try:
        os.remove(dbpath)
    except:
        pass

    conn   = sqlite3.connect(dbpath)
    c      = conn.cursor()
    reader = ReaderFactory.create_reader(filename)


    # Create table fields 
    Field(conn).create()

    # Create variants tables 
    Variant(conn).create(reader.get_fields())
    
    # Create selection 
    Selection(conn).create()
    Selection(conn).insert({"name": "all" , "count": "0"})




    # Insert fields 
    Field(conn).insert_many(reader.get_fields())
    Variant(conn).insert_many(reader.get_variants())

   



def open_db(dbpath):
    engine = create_engine(f"sqlite:///{dbpath}", echo=True)
    Base = automap_base()
    Base.prepare(engine, reflect=True)
    Variants  = Base.classes.variants
    






    # # Create default selection 
    # session.add(Selection(name="all", description="all variant", count = variant_count))
    # session.add(Selection(name="favoris", description="favoris", count = 0))
    
    # session.commit()
