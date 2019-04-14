import pytest
import sys
import os
import sqlite3
import warnings
from cutevariant.core.importer import import_file
from .utils import table_exists


@pytest.fixture
def conn():
    return sqlite3.connect(":memory:")


def test_import_file_vcf(conn):
    path = "exemples/test.vcf"
    import_file(conn, path)



def test_import_file_vcf_gz(conn):
    path = "exemples/test.vcf.gz"
    import_file(conn, path)

def test_import_file_csv(conn):
    path = "exemples/test.csv"
    import_file(conn, path)