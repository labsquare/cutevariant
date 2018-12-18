from PySide2.QtWidgets import *
from PySide2.QtCore import *
import sys
import os
import sqlalchemy
from sqlalchemy import text, select
from cutevariant.core.importer import import_file, open_db
from cutevariant.gui.variantview import *
from cutevariant.core.query import QueryBuilder

if __name__ == "__main__":

    path = "/tmp/cutevariant.db"
    if os.path.exists(path):
        os.remove(path)

    import_file("exemples/test.csv", path)

    engine = sqlalchemy.create_engine(f"sqlite:///{path}", echo=True)
    meta   = sqlalchemy.MetaData(bind=engine)

    builder = QueryBuilder(engine)

    builder2 = QueryBuilder(engine)
    for i in builder2.query():
    	print(i)
	



