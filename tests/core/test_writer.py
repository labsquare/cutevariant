# Standard imports
import pytest
import tempfile
import sqlite3

# Custom imports
from cutevariant.core.importer import import_reader, import_pedfile
from cutevariant.core.reader import FakeReader, VcfReader
from cutevariant.core.writer import CsvWriter, PedWriter


@pytest.fixture
def csvwriter():
    return CsvWriter(tempfile.NamedTemporaryFile("w+"))


@pytest.fixture
def pedwriter():
    return PedWriter(tempfile.NamedTemporaryFile("w+"))


@pytest.fixture
def conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    return conn


def test_csv_writer(conn, csvwriter):
    """Test CSV writer

    - Tabulated file
    - Headers: chr, pos, ref, alt (no id column)
    """

    import_reader(conn, FakeReader())
    csvwriter.save(conn)
    # Test file content
    csvwriter.device.seek(0)
    content = csvwriter.device.read()

    expected = """chr\tpos\tref\talt
11\t125010\tT\tA
12\t125010\tT\tA
13\t125010\tT\tA
"""
    print("Expected:\n'", expected, "'")
    print("Found:\n'", content, "'")

    assert expected == content

    # Delete file
    csvwriter.device.close()


def test_ped_writer(conn, pedwriter):

    reader = VcfReader(open("examples/test.snpeff.vcf"), "snpeff")
    import_reader(conn, reader)
    import_pedfile(conn, "examples/test.snpeff.pedigree.tfam")

    # Test save from DB
    pedwriter.save(conn)

    # Test file content
    pedwriter.device.seek(0)
    content = pedwriter.device.read()

    expected = """fam\tNORMAL\tTUMOR\tNORMAL\t2\t1
fam\tTUMOR\t0\t0\t1\t2
"""
    print("Expected:\n'", expected, "'")
    print("Found:\n'", content, "'")

    assert expected == content


    # Test save from list
    pedwriter.device.seek(0)

    samples = [
        ["fam", "NORMAL", "TUMOR", "NORMAL", "2", "1"],
        # Empty string should be casted into 0 into exported file
        ["fam", "TUMOR", "", "0", "1", "2"],
    ]

    pedwriter.save_from_list(samples)

    # Test file content
    pedwriter.device.seek(0)
    content = pedwriter.device.read()

    print("Expected:\n'", expected, "'")
    print("Found:\n'", content, "'")

    assert expected == content

    # Delete file
    pedwriter.device.close()
