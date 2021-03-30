# Standard imports
import pytest
import tempfile
import sqlite3

# Custom imports
from cutevariant.core.importer import import_reader, import_pedfile
from cutevariant.core.reader import FakeReader, VcfReader
from cutevariant.core.writer import CsvWriter, PedWriter, VcfWriter, BedWriter
from tests import utils


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
            chrom, start, end, _ = tuple(line.split("\t"))
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


def test_csv_writer(conn):
    """Test CSV writer

    - Tabulated file
    - Headers: chr, pos, ref, alt (no id column)
    """

    filename = tempfile.mkstemp()[1]

    # Save file
    with open(filename, "w") as file:
        import_reader(conn, FakeReader())
        csvwriter = CsvWriter(conn, file)
        csvwriter.fields = ["chr", "pos", "alt"]
        csvwriter.save()

    # Read file
    with open(filename, "r") as file:
        content = file.read()

    expected = """chr\tpos\talt
11\t125010\tA
12\t125010\tA
13\t125010\tA
"""

    print("Expected:\n'", expected, "'")
    print("Found:\n'", content, "'")

    assert expected == content


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
    import_reader(conn, reader)
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
    import_reader(conn, VcfReader(open("examples/test.snpeff.vcf")))

    with open(filename, "w", encoding="utf8") as device:
        writer = VcfWriter(conn, device)
        writer.save()

    with open(filename) as file:

        for line in file:
            print(line.strip())
