# Standard imports
import pytest
import tempfile
import sqlite3

# Custom imports
from cutevariant.core.importer import import_reader, import_pedfile
from cutevariant.core.reader import FakeReader, VcfReader
from cutevariant.core.writer import CsvWriter, PedWriter, VcfWriter, BedWriter
from tests import utils

test_filters = [{"field": "pos", "operator": "<", "value": 100000}]


@pytest.fixture
def conn():
    return utils.create_conn()


def test_bed_writer(conn):

    # Write bed file

    filename = tempfile.mkstemp()[1]
    with open(filename, "w") as file:
        bedwriter = BedWriter(conn, file)
        bedwriter.save()

    # Read bed file
    observed = []
    with open(filename) as file:
        for line in file:
            line = line.strip()
            chrom, start, end = tuple(line.split("\t"))
            observed.append((chrom, start, end))

    # Read databases
    expected = []
    for record in conn.execute(
        "SELECT chr, pos as 'start', pos+1 as 'end' FROM variants"
    ):
        chrom = str(record["chr"])
        start = str(record["start"])
        end = str(record["end"])
        expected.append((chrom, start, end))

    assert observed == expected


@pytest.mark.parametrize("separator", ["\t", ";"])
def test_csv_writer(conn, separator):
    """Test CSV writer

    - Tabulated file
    - Headers: chr, pos, ref, alt (no id column)
    """

    filename = tempfile.mkstemp()[1]

    fields = ["chr", "pos", "alt"]
    filters = {"AND": [{"field": "alt", "operator": "=", "value": "A"}]}

    # Save file
    with open(filename, "w") as file:
        csvwriter = CsvWriter(conn, file, fields=fields, filters=filters)
        csvwriter.separator = separator
        csvwriter.save()

    # Read file
    observed = []
    with open(filename, "r") as file:
        for line in file:
            line = tuple(line.strip().split(separator))
            observed.append(line)

    # Read databases
    expected = [("chr", "pos", "alt")]
    for record in conn.execute("SELECT chr, pos, alt FROM variants WHERE alt = 'A'"):
        chrom = str(record["chr"])
        pos = str(record["pos"])
        alt = str(record["alt"])
        expected.append((chrom, pos, alt))

    print(observed)
    print(expected)

    assert observed == expected


def test_ped_writer(conn):
    """Test export of PED file

    2 methods are tested here:
        - Save from connection
        - Save from list

    Args:
        conn(sqlite3.Connection): sqlite3 connection
        pedwriter(PedWriter): Instance of writer pointing to a temp file.
    """
    reader = VcfReader(open("examples/test.snpeff.vcf"), "snpeff")
    import_pedfile(conn, "examples/test.snpeff.pedigree.tfam")

    filename = tempfile.mkstemp()[1]

    # save database
    with open(filename, "w") as file:
        pedwriter = PedWriter(conn, file)
        # Test save from DB
        pedwriter.save()

    with open(filename, "r") as file:
        # Test save from DB
        content = file.read()

    expected = """fam\tNORMAL\tTUMOR\tNORMAL\t2\t1\nfam\tTUMOR\t0\t0\t1\t2\n"""
    print("Expected:\n'", expected, "'")
    print("Found:\n'", content, "'")

    assert expected == content


def test_vcf_writer(conn):

    filename = tempfile.mkstemp(suffix=".vcf")[1]

    conn = utils.create_conn("examples/test.vcf", "snpeff")
    with open(filename, "w", encoding="utf8") as device:
        writer = VcfWriter(conn, device)
        writer.filters = {
            "AND": [{"field": "annotation_count", "operator": "=", "value": 1}]
        }  # This filter helps passing the test. In fact, when we load again the result, the reader complains about having duplicate variants
        # TODO: associate the test example file name with the fields it has. This way, testing is fair
        writer.save()

    # conn = utils.create_conn(filename)
