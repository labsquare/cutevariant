import peewee
from .readerfactory import ReaderFactory
from . import model
import os
from PySide2.QtCore import *


def import_file(filename, db_filename):

    database = peewee.SqliteDatabase(db_filename)
    model.db.initialize(database)

    try:
        os.remove(db_filename)
    except:
        pass

    reader = ReaderFactory.create_reader(filename)

    # create field table
    model.Field.create_table()

    #  Create fields
    model.Field.insert_many(reader.get_fields()).execute()

    model.Variant.create_meta_fields()
    model.Variant.create_table()

    with database.atomic():
        chunk_size = 100
        chunk = []
        for i in reader.get_variants():

            chunk.append(i)

            if len(chunk) == chunk_size:
                model.Variant.insert_many(chunk).execute()
                chunk.clear()

        model.Variant.insert_many(chunk).execute()

    print("done")
