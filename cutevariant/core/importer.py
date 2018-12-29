import os
import csv
import sqlite3
from .readerfactory import ReaderFactory
from .model import Selection, Field, Variant, Sample

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

    # Create table samples
    Sample(conn).create()

    # Create variants tables 
    Variant(conn).create(reader.get_fields())
    
    # Create selection 
    Selection(conn).create()
    Selection(conn).insert({"name": "all" , "count": "0"})

    # insert samples 
    for sample in reader.get_samples():
        Sample(conn).insert({"name":sample, "phenotype":""})

    # Insert fields 
    Field(conn).insert_many(reader.get_fields())
    Variant(conn).insert_many(reader.get_variants())


   




    # # Create default selection 
    # session.add(Selection(name="all", description="all variant", count = variant_count))
    # session.add(Selection(name="favoris", description="favoris", count = 0))
    
    # session.commit()
