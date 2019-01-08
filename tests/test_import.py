import pytest
import sys
import os
import sqlite3
import warnings
from cutevariant.core.importer import import_file
from .utils import table_exists

@pytest.fixture
def conn():
    return  sqlite3.connect(":memory:")




def test_import_file(conn):
	path = "exemples/test.vcf"
	import_file(conn,path)


    














