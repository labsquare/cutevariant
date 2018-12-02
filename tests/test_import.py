import pytest
import sys
import os
import sqlalchemy

from cutevariant.core.importer import import_file
from cutevariant.core.model import create_session, Variant,VariantView,Field,Region


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


def test_view():

    a = VariantView()
    a.name = "test"
    a.sql = "SELECT * FROM variants WHERE chr == 'chr7'"

    b = VariantView()
    b.name = "test2"
    b.sql = "SELECT * FROM variants WHERE chr == 'chr5'"

    c = a + b 
    c.name = "test3"


    session = create_session(engine)
    session.add(a)
    session.add(b)
    session.add(c)

    session.commit()












