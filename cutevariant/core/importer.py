# Standard imports
import os
import csv
import sqlite3

# Custom imports
from .reader.abstractreader import AbstractReader
from .readerfactory import create_reader
from .sql import *


def async_import_reader(conn, reader: AbstractReader, **kwargs):
    """Import data via the given reader into a SQLite database via the given connection

    :param conn: sqlite connection
    :param reader: must be a AbstractReader base class
    :return: yield progression and message
    :rtype: <generator <int>, <str>>
    """
    # Create project
    yield 0, f"Importing data with {reader}"
    create_project(
        conn,
        name=kwargs.get("project_name", "UKN"),
        reference=kwargs.get("reference", "UKN"),
    )

    yield 0, "Creating table shema..."
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
    yield 0, "Inserting samples..."
    insert_many_samples(conn, reader.get_samples())

    # Insert fields
    yield 0, "Inserting fields..."
    insert_many_fields(conn, reader.get_fields())

    # yield 0, "count variants..."
    # total_variant = reader.get_variants_count()

    # Insert variants, link them to annotations and samples
    yield 0, "Inserting variants..."
    percent = 0
    for value, message in async_insert_many_variants(conn, reader.get_variants()):

        if reader.file_size:
            percent = reader.read_bytes / reader.file_size * 100.0
        else:
            # Fallback
            # TODO: useless for now because we don't give the total of variants
            # to async_insert_many_variants()
            percent = value
        yield percent, message

    # Create indexes
    yield 99, "Creating indexes..."
    create_indexes(conn)
    yield 100, "Indexes created."

    # session.add(Selection(name="favoris", description="favoris", count = 0))


def async_import_file(conn, filename, project={}):
    """Import filename into SQLite database

    :param conn: sqlite connection
    :param filenaame: variant filename
    :return: yield progression and message
    """
    # Context manager that wraps the given file
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
