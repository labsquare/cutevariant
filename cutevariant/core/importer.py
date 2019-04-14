import os
import csv
import sqlite3
from .readerfactory import create_reader
from .sql import *


def async_import_file(conn, filename, project={}):
    """
    Import filename into sqlite connection

    :param conn: sqlite connection
    :param filenaame: variant filename 

    :return: yield progression and message

    """

    with create_reader(filename) as reader:

        #  Create projects
        create_project(
            conn, name=project.get("name"), reference=project.get("reference")
        )

        yield 0, "create table shema"
        #  Create table fields
        create_table_fields(conn)

        # Create table samples
        create_table_samples(conn)

        #  Create variants tables
        create_table_variants(conn, reader.get_fields())

        #  Create selection
        create_table_selections(conn)

        yield 0, "insert samples"

        #  insert samples
        for sample in reader.get_samples():
            insert_sample(conn, name=sample)

        # Insert fields
        yield 0, "insert fields"
        insert_many_fields(conn, reader.get_fields())

        yield 0, "count variants..."
        total_variant = reader.get_variants_count()
        yield from insert_many_variants(conn, reader.get_variants(), total_variant)

    # # Create default selection
    # session.add(Selection(name="all", description="all variant", count = variant_count))
    # session.add(Selection(name="favoris", description="favoris", count = 0))

    # session.commit()


def import_file(conn, filename):
    for progress, message in async_import_file(conn, filename):
        #  don't show message
        pass
