from PySide2.QtWidgets import *
from PySide2.QtCore import *
import sys
import os
from cutevariant.core.importer import import_file
from cutevariant.core.query import QueryBuilder
from cutevariant.core.model import Selection, Variant
from cutevariant.gui import MainWindow


import sqlite3

if __name__ == "__main__":

    path = "/tmp/cutevariant.db"
    if os.path.exists(path):
        os.remove(path)

    import_file("exemples/test.csv", path)

    app = QApplication(sys.argv)

    w = MainWindow()

    w.show()

    app.exec_()







 



