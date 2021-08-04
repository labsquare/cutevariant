"""File importer and project creation"""
# Custom imports
from cutevariant import __version__
from .reader.abstractreader import AbstractReader
from .readerfactory import create_reader
from cutevariant.core.reader.pedreader import PedReader
from .sql import (
    create_table_project,
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


from cutevariant import LOGGER


def async_import_reader(
    conn,
    reader: AbstractReader,
    pedfile=None,
    ignored_fields=None,
    indexed_variant_fields=None,
    indexed_annotation_fields=None,
    indexed_sample_fields=None,
    project=None,
):
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

    project = project or dict()

    _project = {"name": "Unknown", "reference": "Unknown"}
    _project.update(project)
    create_table_project(conn, **_project)

    # Create metadatas
    create_table_metadatas(conn)
    metadatas = reader.get_metadatas()
    # Database versioning
    metadatas["cutevariant_version"] = __version__
    insert_many_metadatas(conn, metadatas)

    yield 0, "Creating table shema..."

    ignored_fields = ignored_fields or set()

    reader.ignored_fields = ignored_fields

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
    # index by default
    indexed_variant_fields = indexed_variant_fields or {"pos", "ref", "alt"}
    indexed_annotation_fields = indexed_annotation_fields or set()
    indexed_sample_fields = indexed_sample_fields or set()

    ignored_field_names = {ign[0] for ign in ignored_fields}

    # Very important, before indexing variants: make sure that there are no ignored fields among those we want to index!
    # Ignored fields is a set of (name,category) tuples to ignore

    indexed_variant_fields = indexed_variant_fields.difference(ignored_field_names)

    indexed_annotation_fields = indexed_annotation_fields.difference(
        ignored_field_names
    )
    indexed_sample_fields = indexed_sample_fields.difference(ignored_field_names)

    create_indexes(
        conn, indexed_variant_fields, indexed_annotation_fields, indexed_sample_fields
    )
    yield 100, "Indexes created."

    # session.add(Selection(name="favoris", description="favoris", count = 0))


def async_import_file(
    conn,
    filename,
    pedfile=None,
    ignored_fields=None,
    indexed_variant_fields=None,
    indexed_annotation_fields=None,
    indexed_sample_fields=None,
    project=None,
    vcf_annotation_parser=None,
):
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
    with create_reader(filename, vcf_annotation_parser=vcf_annotation_parser) as reader:
        yield from async_import_reader(
            conn,
            reader,
            pedfile,
            ignored_fields,
            indexed_variant_fields,
            indexed_annotation_fields,
            indexed_sample_fields,
            project,
        )


def import_file(
    conn,
    filename,
    pedfile=None,
    ignored_fields=None,
    indexed_variant_fields=None,
    indexed_annotation_fields=None,
    indexed_sample_fields=None,
    project=None,
    vcf_annotation_parser=None,
):
    """Wrapper for debugging purpose

    TODO: to be deleted
    """
    for progress, message in async_import_file(
        conn,
        filename,
        pedfile,
        ignored_fields,
        indexed_variant_fields,
        indexed_annotation_fields,
        indexed_sample_fields,
        project,
        vcf_annotation_parser,
    ):
        # don't show message
        pass


def import_reader(
    conn,
    reader,
    pedfile=None,
    ignored_fields=None,
    indexed_variant_fields=None,
    indexed_annotation_fields=None,
    indexed_sample_fields=None,
    project={},
):
    """Wrapper for debugging purpose

    TODO: to be deleted
    """
    for progress, message in async_import_reader(
        conn,
        reader,
        pedfile,
        ignored_fields,
        indexed_variant_fields,
        indexed_annotation_fields,
        indexed_sample_fields,
        project,
    ):
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
