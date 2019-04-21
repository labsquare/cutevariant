import os
import csv
import sqlite3
from .reader.abstractreader import AbstractReader
from .readerfactory import create_reader
from .sql import *



def async_import_reader(conn, reader: AbstractReader, **kwargs):
    """
    Import reader into sqlite connection

    :param conn: sqlite connection
    :param reader: must be a AbstractReader base class

    :return: yield progression and message

    """
    # Create projects

    yield 0, f"Import data with {reader}"

    create_project(
        conn,
        name=kwargs.get("project_name", "UKN"),
        reference=kwargs.get("reference", "UKN")
    )

    yield 0, "create table shema"
    # Create table fields
    create_table_fields(conn)

    # # Create table samples
    create_table_samples(conn)

    # Create annotations tables
    create_table_annotations(conn, reader.get_fields_by_category("annotations"))

    # Create variants tables
    create_table_variants(conn, reader.get_fields_by_category("variants"))

    # Create selection
    create_table_selections(conn)

    # Insert samples
    yield 0, "insert samples"
    insert_many_samples(conn, reader.get_samples())

    # Insert fields
    yield 0, "insert fields"
    insert_many_fields(conn, reader.get_fields())

    yield 0, "count variants..."
    # total_variant = reader.get_variants_count()

    yield from async_insert_many_variants(conn, reader.get_variants())

    # # Create default selection
    # session.add(Selection(name="all", description="all variant", count = variant_count))
    # session.add(Selection(name="favoris", description="favoris", count = 0))

    # session.commit()



def async_import_file(conn, filename, project={}):
    """
    Import filename into sqlite connection

    :param conn: sqlite connection
    :param filenaame: variant filename

    :return: yield progression and message

    """

    with create_reader(filename) as reader:
        yield from async_import_reader(conn, reader, **project)


def import_file(conn, filename):
    for progress, message in async_import_file(conn, filename):
        #  don't show message
        pass

def import_reader(conn, reader):
    for progress, message in async_import_reader(conn, reader):
        #  don't show message
        pass
