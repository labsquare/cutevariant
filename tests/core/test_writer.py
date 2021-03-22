# Standard imports
import pytest
import tempfile
import sqlite3

# Custom imports
from cutevariant.core.importer import import_reader, import_pedfile
from cutevariant.core.reader import FakeReader, VcfReader
from cutevariant.core.writer import CsvWriter, PedWriter, VcfWriter


@pytest.fixture
def conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    return conn


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
    print(filename)
    import_reader(conn, VcfReader(open("examples/test.snpeff.vcf")))

    with open(filename, "w") as device:
        writer = VcfWriter(conn, device)

        writer.save()
