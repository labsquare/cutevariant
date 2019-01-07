import pytest
import sys
import os
import sqlite3
import warnings
import json
from cutevariant.core.importer import import_file
from cutevariant.core import Query 

@pytest.fixture
def conn():
    db_path = "/tmp/test_cutevaiant.db"
    import_file("exemples/test.csv", db_path)
    conn = sqlite3.connect(db_path)
    return conn


def test_results(conn):

    builder = Query(conn)
    real_row_number = sum(1 for line in open("exemples/test.csv"))

    # test query output as row by record 
    assert len(list(builder.rows())) == real_row_number - 1 , "wrong record numbers " 
  # test query output as row by record 
    assert len(list(builder.items())) == real_row_number - 1 , "wrong record numbers " 

    # test where clause
    builder.filter = json.loads('''{"AND" : [{"field":"chr", "operator":"==", "value":"chr7"} ]}''')
    assert list(builder.items())[0]["chr"] == "chr7", "where condition failed"

  

    print(builder.sql())
    # assert len(list(builder.rows())) == 1 , "wrong record numbers"

    # Test sample jointure 

    print(builder.sql())
    builder.columns  = ["chr","pos","ref", "alt", "gt(\"sacha\")"]


    conn.close()


def test_detect_samples(conn):
    builder = Query(conn)

    # test regular expression in columns 
    builder.columns  = ["chr","pos","ref", "alt", "gt(\'sacha\')"]
    assert "sacha" in builder.detect_samples().keys(), "cannot detect sacha sample in query columns"

    builder.columns  = ["chr","pos","ref", "alt", "gt(\'sacha\')"]
    assert "sacha" in builder.detect_samples().keys(), "cannot detect sacha sample in query columns"

    builder.columns  = ["chr","pos","ref", "alt", "gt(\'sacha\')", "gt(\"olivier\")"]
    assert "sacha" in builder.detect_samples().keys(), "cannot detect sacha "
    assert "olivier" in builder.detect_samples().keys(), "cannot detect olivier "

    # test where clause 
    builder.columns  = ["chr","pos","ref", "alt"]


    #builder.where = "genotype(\"sacha\").gt = 1"
    #assert "sacha" in builder.detect_samples().keys(), "cannot detect sacha sample in query where clause"

    # test if builder return good samples count 
    builder.columns  = ["chr","pos","ref", "alt", "gt(\'sacha\')", "gt(\"olivier\")"]
    len(set(builder.samples()).intersection(set(["sacha","olivier"]))) == 2  




def test_filter_parser(conn):
    builder = Query(conn)

    raw = '''{"AND" : [{"field":"chr", "operator":"==", "value":"chr7"} ]}'''

    assert builder.filter_to_sql(json.loads(raw)) == "(chr=='chr7')"

    raw = '''
        {
      "AND": [
        
        {"field":"chr", "operator": "==", "value": 3},
        {"field":"chr", "operator": ">", "value": 4}
    ]

    }
    '''

    assert builder.filter_to_sql(json.loads(raw)) == "(chr==3 AND chr>4)"

    raw = '''
    {
      "AND": [
        
        {"field":"chr", "operator": "==", "value": 3},
        {"field":"chr", "operator": ">", "value": 4},
        {
          "OR": [
                {"field":"chr", "operator": "==", "value": 3},
                {"field":"pos", "operator": ">", "value": 322}

            ]
        }
        ]
    }
    '''

    assert builder.filter_to_sql(json.loads(raw)) == "(chr==3 AND chr>4 AND (chr==3 OR pos>322))"






# def test_sample_query():
#     ''' Test join with samples ''' 
#     db_path = "/tmp/test_cutevaiant.db"
#     import_file("exemples/test.csv", db_path)

#     conn = sqlite3.connect(db_path)

#     builder = QueryBuilder(conn)

#     builder.samples = ["sacha","olivier"]

#     print("test",builder.query())


# def test_limit():













