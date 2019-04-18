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
    conn = sqlite3.connect(":memory:")
    import_file(conn, "examples/test.vcf")
    return conn



# def test_query_fields(conn):
#     query = Query(conn)
#     query.columns = ["chr","pos","ref","alt"]
#     assert query.sql() == "SELECT variants.rowid,chr,pos,ref,alt FROM variants"
#     conn.execute(query.sql())

# def test_query_filter(conn):
#     query = Query(conn)
#     query.columns = ["chr","pos","ref","alt"]
#     query.filter = {'AND': 
#             [
#             {'field': 'chr', 'operator': '=', 'value': "chr1"}, 
#             {'field': 'pos', 'operator': '>', 'value': 10}, 
#             {'field': 'pos', 'operator': '<', 'value': 1000}
#             ]}
#     assert query.sql() == "SELECT variants.rowid,chr,pos,ref,alt FROM variants WHERE (chr='chr1' AND pos>10 AND pos<1000)"
#     conn.execute(query.sql())

# def test_query_group_by(conn):
#     query = Query(conn)
#     query.columns = ["chr","pos","ref","alt"]
#     query.group_by = ("chr","pos","ref","alt")

#     conn.execute(query.sql())




# def test_query_selection(conn):

#     query = Query(conn)
#     query.filter = {"AND": [{"field": "ref", "operator": "==", "value": "A"}]}
#     query.create_selection("sacha")

#     query2 = Query(conn)
#     query2.selection = "sacha"

#     for record in query2.items():
#         assert record["ref"] == "A"


# def test_query_from_vql(conn):
#     print("TODO: test query_from_vql")
# query = Query(conn)

# # extract columns and selection
# query.from_vql("SELECT chr,pos FROM all")
# assert query.columns  == ["chr","pos"], "cannot extract columns"
# assert query.selection  == "all", "cannot extract selection"

# #extract where clause as a logic tree
# query.from_vql("SELECT chr,pos,ref FROM all WHERE pos > 3")
# where_clause_1 = query.filter_to_sql({"AND":[{"field":"pos", "operator":">", "value":"3"} ]})
# where_clause_2 = query.filter_to_sql(query.filter)
# assert where_clause_1 == where_clause_1

# # extract genotypes
# query.from_vql("SELECT chr,pos,ref, gt('CGH0157').gt FROM all WHERE pos > 3")
# assert gt('CGH0157').gt in query.columns


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
