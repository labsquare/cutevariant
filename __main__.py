from PySide2.QtWidgets import *
from PySide2.QtCore import *
import sys
import os
from cutevariant.core.importer import import_file
from cutevariant.core import Query
from cutevariant.core.model import Selection, Variant
from cutevariant.gui import MainWindow

from cutevariant.gui.viewquerywidget import ViewQueryWidget
from cutevariant.gui.queryrouter import QueryRouter
from cutevariant.gui.columnquerywidget import ColumnQueryWidget



import sqlite3


if __name__ == "__main__":

    path = "/tmp/cutevariant.db"


    import_file("exemples/test.csv", path)

    conn = sqlite3.connect(path)

    query = Query(conn)
    query.columns = ["chr","pos","ref","alt"]



    app = QApplication(sys.argv)


    w = MainWindow()

    w.show()




    app.exec_()







 



