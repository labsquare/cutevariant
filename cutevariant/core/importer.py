# Standard imports
import os
import csv
import sqlite3
import logging

# Custom imports
from .reader.abstractreader import AbstractReader
from .readerfactory import create_reader
from .sql import *


def async_import_reader(conn, reader: AbstractReader, pedfile=None, project={}):
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
        name=project.get("project_name", "UKN"),
        reference=project.get("reference", "UKN"),
    )

    create_table_metadatas(conn)
    insert_many_metadatas(conn, reader.get_metadatas())

    yield 0, "Creating table shema..."
    # Create table fields
    create_table_fields(conn)

    # Create annotations tables
    create_table_annotations(conn, reader.get_extra_fields_by_category("annotations"))

    # Create variants tables
    create_table_variants(conn, reader.get_extra_fields_by_category("variants"))

    # Create table samples
    create_table_samples(conn, reader.get_extra_fields_by_category("samples"))

    # Create selection
    create_table_selections(conn)

    # Create table sets
    create_table_sets(conn)

    # Insert samples
    yield 0, "Inserting samples..."
    insert_many_samples(conn, reader.get_samples())

    # Get cases and control samples

    if pedfile:
        yield 0, f"Import pedfile {pedfile}"
        import_pedfile(conn, pedfile)

    print(list(get_samples(conn)))

    # Insert fields
    yield 0, "Inserting fields..."
    insert_many_fields(conn, reader.get_extra_fields())

    # Compute control andd cases samples

    control_samples = [
        sample["name"] for sample in get_samples(conn) if sample["phenotype"] == 1
    ]
    case_samples = [
        sample["name"] for sample in get_samples(conn) if sample["phenotype"] == 2
    ]

    yield 0, "Compute case / control"
    yield 0, "controls are " + ",".join(control_samples)
    yield 0, "cases are " + ",".join(case_samples)

    # Insert variants, link them to annotations and samples
    yield 0, "Inserting variants..."
    percent = 0
    variants = reader.get_extra_variants(control=control_samples, case=case_samples)
    for value, message in async_insert_many_variants(conn, variants):

        if reader.file_size:
            percent = reader.read_bytes / reader.file_size * 100

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


    conn.execute("PRAGMA auto_vacuum = FULL")
    # conn.execute("PRAGMA main.cache_size=10000")
    # conn.execute("PRAGMA main.locking_mode=EXCLUSIVE")
    # conn.execute("PRAGMA main.synchronous=NORMAL")
    # conn.execute("PRAGMA main.journal_mode=WAL")
    # conn.execute("PRAGMA main.cache_size=5000")

    # session.add(Selection(name="favoris", description="favoris", count = 0))


def async_import_file(conn, filename, pedfile=None, project={}):
    """Import filename into SQLite database

    :param conn: sqlite connection
    :param filenaame: variant filename
    :return: yield progression and message
    """
    # Context manager that wraps the given file
    with create_reader(filename) as reader:
        yield from async_import_reader(conn, reader, pedfile, project)


def import_file(conn, filename, pedfile=None, project={}):
    for progress, message in async_import_file(conn, filename, pedfile, project):
        #  don't show message
        pass


def import_reader(conn, reader, pedfile=None, project={}):
    for progress, message in async_import_reader(conn, reader, pedfile, project):
        #  don't show message
        pass


def import_pedfile(conn, filename):
    """import *.fam file into sample table

    data has the same structure of a fam file object
    https://www.cog-genomics.org/plink/1.9/formats#fam

    the file is a tabular with the following column 

    Family String Id : "Fam"
    Sample String Id: "Boby"
    Father String Id
    Mother String Id
    Sex code:  (1 = male, 2 = female, 0 = unknown)
    Phenotype code: (1 = control, 2 = case, 0 = missing data if case/control)
    
    Arguments:
        conn {[type]} -- [description]
        data {list} -- [description]
    """

    with open(filename) as file:
        reader = csv.reader(file, delimiter="\t")

        sample_map = dict(
            [(sample["name"], sample["id"]) for sample in get_samples(conn)]
        )
        sample_names = list(sample_map.keys())

        for line in reader:
            if len(line) >= 6:
                fam = line[0]
                name = line[1]
                father = line[2]
                mother = line[3]
                sexe = line[4]
                phenotype = line[5]

                sexe = int(sexe) if sexe.isdigit() else 0
                phenotype = int(phenotype) if phenotype.isdigit() else 0

                if name in sample_names:
                    edit_sample = {
                        "id": sample_map[name],
                        "fam": fam,
                        "sex": sexe,
                        "phenotype": phenotype,
                    }

                    if father in sample_names:
                        edit_sample["father_id"] = sample_map[father]

                    if mother in sample_names:
                        edit_sample["mother_id"] = sample_map[mother]

                    update_sample(conn, edit_sample)
