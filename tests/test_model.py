import pytest
import sqlite3
import os
from cutevariant.core.model import Selection, Field, Variant 
from cutevariant.core.importer import import_file
from .utils import table_exists, table_count


@pytest.fixture
def conn():
    db_path = "/tmp/test_cutevaiant_model.db"
    try:
        os.remove(db_path)
    except:
        pass

    return sqlite3.connect(db_path)


def test_selection(conn):
    #import_file("exemples/test.csv", db_path)
    
    Selection(conn).create()
    assert table_exists("selections",conn), "table selection cannot be create"
    assert table_exists("selection_has_variant",conn), "table selection_has_variant cannot be create"

    Selection(conn).insert({
        "name": "test",
        "count": 100,
        "truc": 44
        })

    assert table_count("selections",conn) == 1

    conn.close()



def test_field(conn):
    #import_file("exemples/test.csv", db_path)
    
    Field(conn).create()
    assert table_exists("fields",conn), "table fields cannot be create"

    conn.close()
