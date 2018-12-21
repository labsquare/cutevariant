from PySide2.QtWidgets import *
from PySide2.QtCore import *
import sys
import os
from cutevariant.core.importer import import_file
from cutevariant.gui.variantview import VariantView
from cutevariant.core.query import QueryBuilder
from cutevariant.core.model import Selection, Variant
import sqlite3

if __name__ == "__main__":

    path = "/tmp/cutevariant.db"
    if os.path.exists(path):
        os.remove(path)

    import_file("exemples/test.csv", path)

    conn   = sqlite3.connect(path)

    query = QueryBuilder(conn)

    app = QApplication(sys.argv)

    view = VariantView()
    view.load(query)
    view.show()

    app.exec_()







 



