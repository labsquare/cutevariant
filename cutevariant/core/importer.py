"""File importer and project creation"""
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
    create_table_wordsets,
    insert_many_samples,
    get_samples,
    insert_many_fields,
    async_insert_many_variants,
    create_indexes,
    update_sample,
)
from cutevariant.commons import logger

LOGGER = logger()


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
    create_table_wordsets(conn)

    # Insert samples
    yield 0, "Inserting samples..."
    insert_many_samples(conn, reader.get_samples())

    # Import PED file
    if pedfile:
        yield 0, f"Import pedfile {pedfile}"
        import_pedfile(conn, pedfile)

        # Compute control and cases samples
        samples = tuple(get_samples(conn))
        LOGGER.debug("Check found samples in DB after PED import: %s", samples)
        control_samples = [
            sample["name"] for sample in samples if sample["phenotype"] == 1
        ]
        case_samples = [
            sample["name"] for sample in samples if sample["phenotype"] == 2
        ]
        yield 0, "Compute phenotypes from samples:"
        yield 0, "- Found controls are: [" + ",".join(control_samples) + "]"
        yield 0, "- Found cases are: [" + ",".join(case_samples) + "]"
    else:
        control_samples = list()
        case_samples = list()

    # Insert fields
    yield 0, "Inserting fields..."
    insert_many_fields(conn, reader.get_extra_fields())

    # Insert variants, link them to annotations and samples
    yield 0, "Insertings variants..."
    variants = reader.get_extra_variants(control=control_samples, case=case_samples)
    yield from async_insert_many_variants(
        conn, variants, total_variant_count=reader.number_lines
    )

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
    r"""Import \*.tfam file (PLINK sample information file) into samples table

    See Also:
        :meth:`cutevariant.core.reader.pedreader.PedReader`
    """
    [
        update_sample(conn, sample)
        for sample in PedReader(filename, get_samples(conn), raw_samples=False)
    ]
