import pytest
import sys
import os
import sqlalchemy

from cutevariant.core.importer import import_file
from cutevariant.core.model import create_session, Variant,Field,Selection
from cutevariant.core.query import QueryBuilder

'''
connect to database 
'''
path = "/tmp/cutevariant.db"
if os.path.exists(path):
    os.remove(path)

engine = sqlalchemy.create_engine(f"sqlite:///{path}", echo=False)


def test_import_csv():
    # import file 
    import_file("exemples/test.csv", engine)

    # test data 
    session = create_session(engine)
    assert session.query(Variant).count() == 5
    assert session.query(Field).count() == 4


def test_query():
    q = QueryBuilder(engine)
    q.fields = ["chr","pos"]
    q.condition = "variants.id > 0"
    for i in q:
        print(i)


def test_query_selection():
    q = QueryBuilder(engine)
    q.fields = ["chr","pos"]

    A = q.query()


    q.condition = "variants.id > 3"
    q.create_selection("sacha")

    session = create_session(engine)


    q.selection_name = "sacha"
    q.condition = "variants.chr == 'chr8'"


    print("selection A")
    for i in A:
        print(i)

    B  = q.query()

    print("selection B")
    for i in B:
        print(i)


    print("selection C")

    C = A.except_(B)

    for i in C:
        print(i)

    # print("selection")
    # query = session.query(Variant).join(Selection, Variant.selections).filter(Selection.name == "sacha")
    # for i in query.filter(sqlalchemy.text("variants.id > 0")):
    #     print(i)
    


















