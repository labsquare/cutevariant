import os
import csv
import sqlite3
from .readerfactory import ReaderFactory
from .sql import *


def import_file(conn, filename):

    print("import file ", filename)

    reader = ReaderFactory.create_reader(filename)

    #  Create table fields
    create_table_fields(conn)

    # Create table samples
    create_table_samples(conn)

    #  Create variants tables
    create_table_variants(conn, reader.get_fields())

    #  Create selection
    create_table_selections(conn)

    #  insert samples
    for sample in reader.get_samples():
        insert_sample(conn, name=sample)

    # Insert fields
    insert_many_fields(conn, reader.get_fields())
    insert_many_variants(conn, reader.get_variants())

    # # Create default selection
    # session.add(Selection(name="all", description="all variant", count = variant_count))
    # session.add(Selection(name="favoris", description="favoris", count = 0))

    # session.commit()
