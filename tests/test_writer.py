# Standard imports
import pytest
import sqlite3
import tempfile


# Custom imports
from cutevariant.core.importer import import_reader
from cutevariant.core.reader import FakeReader
from cutevariant.core.writer import CsvWriter, AbstractWriter
import sqlite3


WRITERS = [
    CsvWriter(tempfile.NamedTemporaryFile("w"))
    ]


@pytest.mark.parametrize(
    "writer", WRITERS, ids=[str(i.__class__.__name__) for i in WRITERS]
)
def test_writer(writer):
    
    conn = sqlite3.connect(":memory:")
    import_reader(conn, FakeReader())
    reader = FakeReader()
    writer.save(conn)
    writer.device.close()



