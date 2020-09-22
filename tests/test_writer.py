# Standard imports
import pytest
import tempfile
import sqlite3

# Custom imports
from cutevariant.core.importer import import_reader
from cutevariant.core.reader import FakeReader
from cutevariant.core.writer import CsvWriter, AbstractWriter


WRITERS = [CsvWriter(tempfile.NamedTemporaryFile("w+"))]


@pytest.mark.parametrize(
    "writer", WRITERS, ids=[str(i.__class__.__name__) for i in WRITERS]
)
def test_writer(writer):

    conn = sqlite3.connect(":memory:")
    import_reader(conn, FakeReader())
    writer.save(conn)

    # Test file content
    writer.device.seek(0)
    content = writer.device.read()
    print("Content:", content)

    expected = """1\t11\t125010\tT\tA
2\t12\t125010\tT\tA
3\t13\t125010\tT\tA
"""
    assert content == expected

    # Delete file
    writer.device.close()
