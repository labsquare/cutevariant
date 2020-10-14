# Standard imports
import pytest
import tempfile
import sqlite3

# Custom imports
from cutevariant.core.importer import import_reader
from cutevariant.core.reader import FakeReader
from cutevariant.core.writer import CsvWriter


WRITERS = [CsvWriter(tempfile.NamedTemporaryFile("w+"))]


@pytest.mark.parametrize(
    "writer", WRITERS, ids=[str(i.__class__.__name__) for i in WRITERS]
)
def test_csv_writer(writer):
    """Test CSV writer

    - Tabulated file
    - Headers: chr, pos, ref, alt (no id column)
    """
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    import_reader(conn, FakeReader())
    writer.save(conn)

    # Test file content
    writer.device.seek(0)
    content = writer.device.read()

    expected = """chr\tpos\tref\talt
11\t125010\tT\tA
12\t125010\tT\tA
13\t125010\tT\tA
"""
    print("Expected:\n'", expected, "'")
    print("Found:\n'", content, "'")

    assert expected == content

    # Delete file
    writer.device.close()
