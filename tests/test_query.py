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
    os.remove("/tmp/test.db")
    conn = sqlite3.connect("/tmp/test.db")
    import_file(conn,"exemples/test.vcf")
    return conn




# def test_set_operation(conn):
#     pass 
    # query = Query(conn)

    # query.filter = {"AND" : [{"field":"ref", "operator":"==", "value":"A"} ]}

    # print(query.sql())

# def test_detect_samples(conn):
#     builder = Query(conn)

    # test regular expression in columns 
    # builder.columns  = ["chr","pos","ref", "alt", "gtsacha.gt"]
    # assert "sacha" in builder.detect_samples().keys(), "cannot detect sacha sample in query columns"

    # builder.columns  = ["chr","pos","ref", "alt", "gtsacha.gt"]
    # assert "sacha" in builder.detect_samples().keys(), "cannot detect sacha sample in query columns"

    # builder.columns  = ["chr","pos","ref", "alt", "gtsacha.gt", "gtsacha.gt"]
    # assert "sacha" in builder.detect_samples().keys(), "cannot detect sacha "
    # assert "olivier" in builder.detect_samples().keys(), "cannot detect olivier "

    # # test where clause 
    # builder.columns  = ["chr","pos","ref", "alt"]


    # #builder.where = "genotype(\"sacha\").gt = 1"
    # #assert "sacha" in builder.detect_samples().keys(), "cannot detect sacha sample in query where clause"

    # # test if builder return good samples count 
    # builder.columns  = ["chr","pos","ref", "alt", "gtsacha.gt", "gtsacha.gt"]
    # len(set(builder.samples()).intersection(set(["sacha","olivier"]))) == 2  




# def test_filter_parser(conn):
#     pass
    # builder = Query(conn)

    # raw = '''{"AND" : [{"field":"chr", "operator":"==", "value":"chr7"} ]}'''

    # assert builder.filter_to_sql(json.loads(raw)) == "(chr=='chr7')"

    # raw = '''
    #     {
    #   "AND": [
        
    #     {"field":"chr", "operator": "==", "value": 3},
    #     {"field":"chr", "operator": ">", "value": 4}
    # ]

    # }
    # '''

    # assert builder.filter_to_sql(json.loads(raw)) == "(chr==3 AND chr>4)"

    # raw = '''
    # {
    #   "AND": [
        
    #     {"field":"chr", "operator": "==", "value": 3},
    #     {"field":"chr", "operator": ">", "value": 4},
    #     {
    #       "OR": [
    #             {"field":"chr", "operator": "==", "value": 3},
    #             {"field":"pos", "operator": ">", "value": 322}

    #         ]
    #     }
    #     ]
    # }
    # '''

    # assert builder.filter_to_sql(json.loads(raw)) == "(chr==3 AND chr>4 AND (chr==3 OR pos>322))"






# def test_sample_query():
#     ''' Test join with samples ''' 
#     db_path = "/tmp/test_cutevaiant.db"
#     import_file("exemples/test.csv", db_path)

#     conn = sqlite3.connect(db_path)

#     builder = QueryBuilder(conn)

#     builder.samples = ["sacha","olivier"]

#     print("test",builder.query())


# def test_limit():













