# Standard imports
import os
import csv
import sqlite3
import logging

# Custom imports
from .reader.abstractreader import AbstractReader
from .readerfactory import create_reader
from .sql import *



def test(boby:int, test = "test"):
    """Summary
    
    Args:
        boby (int): Description
        test (str, optional): Description
    """
    pass

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



    # Create annotations tables
    create_table_annotations(conn, reader.get_extra_fields_by_category("annotations"))

    # Create variants tables
    create_table_variants(conn, reader.get_extra_fields_by_category("variants"))

    # Create table samples
    create_table_samples(conn, reader.get_extra_fields_by_category("samples"))

    # Create selection
    create_table_selections(conn)

    # Insert samples
    yield 0, "Inserting samples..."
    insert_many_samples(conn, reader.get_samples())

    # Insert fields
    yield 0, "Inserting fields..."
    insert_many_fields(conn, reader.get_extra_fields())

    # yield 0, "count variants..."
    # total_variant = reader.get_variants_count()

    # Insert variants, link them to annotations and samples
    yield 0, "Inserting variants..."
    percent = 0
    for value, message in async_insert_many_variants(conn, reader.get_extra_variants()):

        if reader.file_size:
            percent = reader.read_bytes / reader.file_size * 100 

           
        else:
            # Fallback
            # TODO: useless for now because we don't give the total of variants
            # to async_insert_many_variants()
            percent = value
        yield percent, message


    # Insert sample data   
    sample_data = kwargs.get("sample_data", None)
    # TODO ...

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

def import_familly(conn, filename):
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

        sample_map = dict([(sample["name"], sample["id"]) for sample in get_samples(conn)])
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
                        "id" : sample_map[name],
                        "fam": fam,
                        "sexe": sexe,
                        "phenotype": phenotype
                    }

                    if father in sample_names:
                        edit_sample["father_id"] = sample_map[father]
                    
                    if mother in sample_names:
                        edit_sample["mother_id"] = sample_map[mother]

                    update_sample(conn, edit_sample)

            
   