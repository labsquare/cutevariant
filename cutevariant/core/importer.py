import os
import csv
import sqlite3
from .readerfactory import ReaderFactory
from .sql import *


def import_file(filename, dbpath):

    try:
        os.remove(dbpath)
    except:
        pass

    conn = sqlite3.connect(dbpath)
    c = conn.cursor()
    reader = ReaderFactory.create_reader(filename)

    #  Create table fields
    create_table_fields(conn)

    # Create table samples
    create_table_samples(conn)

    #  Create variants tables
    create_table_variants(reader.get_fields())


    #  Create selection
    create_table_selections(conn)
    insert_selection(name = "all", count = 0)

    #  insert samples
    for sample in reader.get_samples():
        insert_sample(name = sample)

    # Insert fields
    Field(conn).insert_many(reader.get_fields())
    Variant(conn).insert_many(reader.get_variants())

    # # Create default selection
    # session.add(Selection(name="all", description="all variant", count = variant_count))
    # session.add(Selection(name="favoris", description="favoris", count = 0))

    # session.commit()
