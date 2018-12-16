from PySide2.QtWidgets import *
from PySide2.QtCore import *
import sys
import os

import sqlalchemy
from sqlalchemy import text
from cutevariant.core.importer import import_file
from cutevariant.core.model import create_session, Variant
from cutevariant.core.query import QueryBuilder
from cutevariant.gui.variantview import *


if __name__ == "__main__":

    path = "/tmp/cutevariant.db"
    if os.path.exists(path):
        os.remove(path)

    engine = sqlalchemy.create_engine(f"sqlite:///{path}", echo=True)
    import_file("exemples/test.csv", engine)


    builder = QueryBuilder(engine)


    app = QApplication(sys.argv)
    w = VariantView()
    builder.fields = ["chr","pos","ref","alt"]

    w.load(builder.to_list())




    #w.load(engine)

    w.show()

    app.exec_()
