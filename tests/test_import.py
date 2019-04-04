import pytest
import sys
import os
import sqlite3
import warnings
from cutevariant.core.importer import import_file
from cutevariant.core.reader import VcfReader, FakeReader
import os
from .utils import table_exists

READERS = [FakeReader()]

@pytest.fixture
def conn():
    try:
        os.remove("/tmp/test.db")
    except:
        pass
    return sqlite3.connect("/tmp/test.db")

def test_import_file_vcf(conn):


    path = "examples/test.vcf"
    import_file(conn, path)


# def test_import_file_vcf_gz(conn):
#     path = "exemples/test.vcf.gz"
#     import_file(conn, path)

# def test_import_file_csv(conn):
#     path = "exemples/test.csv"
#     import_file(conn, path)
