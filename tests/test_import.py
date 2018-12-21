import pytest
import sys
import os
import sqlite3
import warnings
from cutevariant.core.importer import import_file
from .utils import table_exists

def test_import_database():
    db_path = "/tmp/test_cutevaiant.db"
    import_file("exemples/test.csv", db_path)
    
    assert os.path.isfile(db_path) == True, "database doesn't exists"

    conn = sqlite3.connect(db_path)

    assert table_exists("fields", conn), "fields table doesn't exists"
    assert table_exists("variants", conn), "variant table doesn't exists"
    assert table_exists("selections", conn), "selections table doesn't exists"
    assert table_exists("selection_has_variant", conn), "selection_has_variants table doesn't exists"


    conn.close()
















