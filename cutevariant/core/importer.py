"""File importer and project creation"""
# Standard imports
import csv

# Custom imports
from cutevariant import __version__
from .reader.abstractreader import AbstractReader
from .readerfactory import create_reader
from cutevariant.core.reader.pedreader import PedReader
from .sql import (
    create_project,
    create_table_metadatas,
    insert_many_metadatas,
    create_table_fields,
    create_table_annotations,
    create_table_variants,
    create_table_samples,
    create_table_selections,
    create_table_sets,
    insert_many_samples,
    get_samples,
    insert_many_fields,
    async_insert_many_variants,
    create_indexes,
    update_sample,
)


def async_import_reader(conn, reader: AbstractReader, pedfile=None, project={}):
    """Import data via the given reader into a SQLite database via the given connection

    :param conn: sqlite connection
    :param reader: must be a AbstractReader base class
    :param pedfile: PED file path
    :param project: The reference genome and the name of the project.
        Keys have to be at least "reference" and "project_name".
    :type project: <dict>
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

    # Create metadatas
    create_table_metadatas(conn)
    metadatas = reader.get_metadatas()
    # Database versioning
    metadatas["cutevariant_version"] = __version__
    insert_many_metadatas(conn, metadatas)

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

    # Import PED file
    # TODO: PED files are ALWAYS imported; WTF ?
    if pedfile:
        # TODO: Attention ceci est systématiquement appelé et vient
        #  écraser/mettre à jour les samples donnés avec le fichier de variants
        yield 0, f"Import pedfile {pedfile}"
        import_pedfile(conn, pedfile)

    # TODO: most of the time these lists are empty, are they tied to pedfile indentation ?
    # TODO: can you document the code in get_extra_variants plz?
    # Compute control and cases samples
    control_samples = [
        sample["name"] for sample in get_samples(conn) if sample["phenotype"] == 1
    ]
    case_samples = [
        sample["name"] for sample in get_samples(conn) if sample["phenotype"] == 2
    ]

    yield 0, "Compute phenotypes: case/control"
    yield 0, "- controls are [" + ",".join(control_samples) + "]"
    yield 0, "- cases are [" + ",".join(case_samples) + "]"

    print(list(get_samples(conn)))

    # Insert fields
    yield 0, "Inserting fields..."
    insert_many_fields(conn, reader.get_extra_fields())

    # Insert variants, link them to annotations and samples
    yield 0, "Inserting variants..."
    # TODO: can you document the code in get_extra_variants plz?
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

    # session.add(Selection(name="favoris", description="favoris", count = 0))


def async_import_file(conn, filename, pedfile=None, project={}):
    """Import filename into SQLite database

    :param conn: sqlite connection
    :param filename: variant filename
    :param pedfile: PED file path
    :param project: The reference genome and the name of the project.
        Keys have to be at least "reference" and "project_name".
    :type project: <dict>
    :return: yield progression and message
    """
    # Context manager that wraps the given file and creates an apropriate reader
    with create_reader(filename) as reader:
        yield from async_import_reader(conn, reader, pedfile, project)


def import_file(conn, filename, pedfile=None, project={}):
    """Wrapper for debugging purpose

    TODO: to be deleted
    """
    for progress, message in async_import_file(conn, filename, pedfile, project):
        # don't show message
        pass


def import_reader(conn, reader, pedfile=None, project={}):
    """Wrapper for debugging purpose

    TODO: to be deleted
    """
    for progress, message in async_import_reader(conn, reader, pedfile, project):
        # don't show message
        pass


def import_pedfile(conn, filename):
    """Import *.fam file (PLINK sample information file) into samples table

    See Also:
        :meth:`cutevariant.core.reader.pedreader.PedReader`

    Arguments:
        conn {[type]} -- [description]
        data {list} -- [description]
    """
    [
        update_sample(conn, sample)
        for sample in PedReader(filename, get_samples(conn), raw_samples=False)
    ]
