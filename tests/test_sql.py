import pytest
import sqlite3
import os
from cutevariant.core import sql
from .utils import table_exists, table_count, table_drop


@pytest.fixture
def conn():
    _conn = sqlite3.connect(":memory:")
    table_drop(_conn, "fields")
    table_drop(_conn, "samples")
    table_drop(_conn, "variants")
    table_drop(_conn, "selections")

    return _conn
    


def test_fields(conn):


    fields = [
    {"name":"field1", "category": "variants", "type" : "text", "description" : "empty"},
    {"name":"field2", "category": "variants", "type" : "text", "description" : "empty"},
    {"name":"field3", "category": "variants", "type" : "text", "description" : "empty"},
    {"name":"field4", "category": "variants", "type" : "text", "description" : "empty"}
    ]

    sql.create_table_fields(conn)
    assert table_exists(conn,"fields"), "cannot create table fields"


    sql.insert_field(conn, **fields[0])
    assert table_count(conn,"fields") == 1, "cannot insert fields"

    sql.insert_many_fields(conn,fields[1:])
    assert table_count(conn,"fields") == len(fields), "cannot insert amny fields"

    for index, f in enumerate(sql.get_fields(conn)):
        assert f == fields[index]

def test_samples(conn):

    sql.create_table_samples(conn)
    assert table_exists(conn,"samples"), "cannot create table samples"

    samples = ["sacha", "boby","guillaume"]

    for to_insert in samples:
        sql.insert_sample(conn,to_insert)

    assert [sample["name"] for sample in sql.get_samples(conn)] == samples

def test_selections(conn):
    sql.create_table_selections(conn)
    assert table_exists(conn,"selections"), "cannot create table selections"  
    sql.insert_selection(conn, name = "variants", count = 10)
    assert table_count(conn,"selections") == 1, "cannot insert selection"


def test_variants(conn):


    fields = [
    {"name":"chr", "category": "variants", "type" : "text", "description" : "chromosome"},
    {"name":"pos", "category": "variants", "type" : "int", "description" : "position"},
    {"name":"ref", "category": "variants", "type" : "text", "description" : "reference"},
    {"name":"alt", "category": "variants", "type" : "text", "description" : "alternative"},
    {"name":"extra1", "category": "variants", "type" : "float", "description" : "annotation 1"},
    {"name":"extra2", "category": "variants", "type" : "int", "description" : "annotation 2"}
    ]

    sql.create_table_fields(conn)
    assert table_exists(conn,"fields"), "cannot create table fields"

    sql.create_table_samples(conn)
    assert table_exists(conn,"samples"), "cannot create table samples"

    sql.insert_many_fields(conn,fields)
    assert table_count(conn,"fields") == len(fields), "cannot insert amny fields"

    sql.create_table_variants(conn, sql.get_fields(conn))
    assert table_exists(conn,"variants"), "cannot create table variants"


    variants = [
    {"chr": "chr4", "pos": 324, "ref": "A", "alt":"C", "extra1": 3.2, "extra2": 100},
    {"chr": "chr1", "pos": 324, "ref": "C", "alt":"C", "extra1": 3.2, "extra2": 100},
    {"chr": "chr24", "pos": 324, "ref": "G", "alt":"C", "extra1": 3.2, "extra2": 100},
    {"chr": "chr234", "pos":324, "ref": "A", "alt":"C", "extra1": 3, "extra2": 100.0},
    {"chr": "chr52", "pos": 324, "ref": "T", "alt":"C", "extra1": 3.2, "extra2": 100},
    ]

    sql.insert_many_variants(conn,variants)

    cursor = conn.cursor()


    for i, record in enumerate(cursor.execute("SELECT * FROM variants")):
        assert(record == tuple(variants[i].values()))


def test_intersection(conn):
    pass   
    # from cutevariant.core.importer import import_file
    # path = "exemples/test.vcf"
    # import_file(conn,path)
    
    # q1 = "SELECT * FROM variants WHERE ref='A'"
    # q2 = "SELECT * FROM variants WHERE alt = 'G'"

    # cursor = conn.cursor()

    # q1_count = len(list(cursor.execute(q1)))
    # q2_count = len(list(cursor.execute(q2)))

    # print(q1_count)
    # print(q2_count)

    # for record in cursor.execute(sql.intersect(q1,q2)).fetchall():
    #     ref = record[2]
    #     alt = record[3]

    #     assert ref == "A" and alt == "G"
        

def test_intersection(conn):
    pass
    # from cutevariant.core.importer import import_file
    # path = "exemples/test.vcf"
    # import_file(conn,path)
    
    # q1 = "SELECT * FROM variants WHERE ref='A'"
    # q2 = "SELECT * FROM variants WHERE alt = 'G'"

    # cursor = conn.cursor()

    # q1_count = len(list(cursor.execute(q1)))
    # q2_count = len(list(cursor.execute(q2)))

    # print(q1_count)
    # print(q2_count)

    # for record in cursor.execute(sql.union(q1,q2)).fetchall():
    #     ref = record[2]
    #     alt = record[3]

    #     assert ref == "A" and alt == "G"
