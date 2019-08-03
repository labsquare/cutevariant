import pytest
import copy
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


def test_query_columns(conn):
    """
    .. note:: Now when no annotation column is selected, we do not make a join on this table
        " LEFT JOIN annotations ON annotations.variant_id = variants.id"
        is not in basic sql() query anymore
    """
    query = Query(conn)
    query.columns = ["chr", "pos", "ref", "alt"]
    # Test normal query: children, joint to annotations, group by added
    s = query.sql()

    pass
    assert (
        query.sql()
        == "SELECT variants.id,`chr`,`pos`,`ref`,`alt`,COUNT(*) as 'children' FROM variants GROUP BY chr,pos,ref,alt"
    )

    # Test basic query: no children, no useless annotations joint except if it is needed by cols or filter
    assert (
        query.sql(do_not_add_default_things=True)
        == "SELECT `chr`,`pos`,`ref`,`alt` FROM variants GROUP BY chr,pos,ref,alt"
    )

    # Count query => remove everything that is not needed in filter
    assert (
        query.sql_count()
        == "SELECT variants.id FROM variants"
    )

    # All group by different from chr,pos,ref,alt modifies the nb of variant => added
    query.group_by = ["chr", "pos"]
    assert (
        query.sql_count()
        == "SELECT variants.id FROM variants GROUP BY chr,pos"
    )

    # No group by: no children, no group by
    query.group_by = None
    assert (
        query.sql()
        == "SELECT variants.id,`chr`,`pos`,`ref`,`alt` FROM variants"
    )






def test_query_filter(conn):
    """
    . note:: Now when no annotation column is selected, we do not make a join on this table
        " LEFT JOIN annotations ON annotations.variant_id = variants.id"
        is not in basic sql() query anymore
    """
    query = Query(conn)
    query.columns = ["chr", "pos", "ref", "alt"]
    query.group_by = None
    query.filter = {
        "AND": [
            {"field": "chr", "operator": "=", "value": "'chr1'"},
            {"field": "pos", "operator": ">", "value": 10},
            {"field": "pos", "operator": "<", "value": 1000},
            {"field": "ref", "operator": "IN", "value": "('A', 'T')"},
            {"field": "ref", "operator": "NOT IN", "value": "('G', 'C')"},
        ]
    }

    # todo : cannot break the lines...
    expected = "SELECT variants.id,`chr`,`pos`,`ref`,`alt` FROM variants WHERE (chr = 'chr1' AND pos > 10 AND pos < 1000 AND ref IN ('A', 'T') AND ref NOT IN ('G', 'C'))"
    
    q = query.sql()
    assert query.sql() == expected
    conn.execute(query.sql())


def test_query_functions(conn):
    """Test the extraction of samples and the join clause to sample_has_variant
    Expected query:
    SELECT variants.id,chr,pos,ref,alt,`gt_TUMOR`.gt FROM variants
    LEFT JOIN annotations ON annotations.variant_id = variants.id
    LEFT JOIN sample_has_variant gt_NORMAL ON gt_NORMAL.variant_id = variants.id AND gt_NORMAL.sample_id = 1
    LEFT JOIN sample_has_variant gt_TUMOR ON gt_TUMOR.variant_id = variants.id AND gt_TUMOR.sample_id = 2
    WHERE (chr = 'chr1' AND pos > 10 AND pos < 1000 AND gt_NORMAL.GT == 1)
    """
    query = Query(conn)

    query.columns = ["chr", "pos", "ref", "alt", ("genotype", "TUMOR", "gt")]
    query.filter = {
        "AND": [
            {"field": "chr", "operator": "=", "value": "'chr1'"},
            {"field": "pos", "operator": ">", "value": 10},
            {"field": "pos", "operator": "<", "value": 1000},
            {"field": ("genotype", "NORMAL", "GT"), "operator": "==", "value": 1},
        ]
    }

    # Detect genotype in columns
    query.extract_samples_from_columns_and_filter()
    assert "TUMOR" in query._samples_to_join

    # Detect genotype in filters
    assert "NORMAL" in query._samples_to_join

    # Join to sample_has_variant
    sql_query = query.sql()
    assert "LEFT JOIN sample_has_variant" in sql_query
    # Column
    assert "`gt_TUMOR`.gt" in sql_query
    # Filter
    assert "`gt_NORMAL`.GT" in sql_query

    sql_query = query.sql_count()
    # No cols in annotation => remove dependency
    assert "LEFT JOIN annotations" not in sql_query
    # In column => remove dependency
    assert "`gt_TUMOR`.gt" not in sql_query
    # In filter => keep dependency
    assert "`gt_NORMAL`.GT" in sql_query


    query.columns = ["chr", "pos", "ref", "alt", "transcript"]
    sql_query = query.sql_count()
    # col in cols only => remove dependency
    assert "LEFT JOIN annotations" not in sql_query


    query.filter["AND"].append({"field": "transcript", "operator": "=", "value": "test"})
    sql_query = query.sql_count()
    # filter transcript in annotations => keep dependency
    assert "LEFT JOIN annotations" in sql_query


def test_csv_export():
    """More or less the copy of the code in ViewQueryWidget
    """
    # Need file with annotations
    conn = sqlite3.connect(":memory:")
    import_file(conn, "examples/test.vep.vcf")

    query = Query(conn)
    # Two columns: 1 in variants table, 1 in annotations table
    # The next query should return all variants and their annotations
    # Many annotations for each variant: so as many rows as annotations number
    query.columns = ["chr", "transcript"]

    # Duplicate the current query, but remove automatically added columns
    # and remove group by/order by commands.
    # Columns are kept as they are selected in the GUI
    query = copy.copy(query)
    query.group_by = None
    query.order_by = None
    # Query the database
    ret = [tuple(row) for row in query.conn.execute(query.sql(do_not_add_default_things=True))]

    annotations_count = tuple(*query.conn.execute("SELECT COUNT(*) FROM annotations"))
    found = len(ret)
    expected = annotations_count[0] # 71
    assert expected == found == 71

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
