import pytest
import sys
import os
import sqlite3
import warnings
from cutevariant.core.importer import import_file
from cutevariant.core.query import QueryBuilder 

def test_import_database():
    db_path = "/tmp/test_cutevaiant.db"
    import_file("exemples/test.csv", db_path)

    conn = sqlite3.connect(db_path)

    builder = QueryBuilder(conn)

    # test line number 
    num_lines = sum(1 for line in open("exemples/test.csv"))

    assert len(list(builder.rows())) == num_lines - 1 , "wrong record numbers"

    builder.where = "chr == 'chr5'"
    assert len(list(builder.rows())) == 1 , "wrong record numbers"


    
    conn.close()
















