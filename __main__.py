from PySide2.QtWidgets import *
from PySide2.QtCore import *
import sys
import os
from cutevariant.core.importer import import_file
from cutevariant.core import Query
from cutevariant.core.model import Selection, Variant
from cutevariant.gui import MainWindow

from cutevariant.gui.abstractquerywidget import AbstractQueryWidget
from cutevariant.gui.queryrouter import QueryRouter


import sqlite3


class TestWidget(AbstractQueryWidget):
	def __init__(self):
		super().__init__()

		self.b = QPushButton("salut")
		layout = QVBoxLayout()
		layout.addWidget(self.b)
		self.setLayout(layout)

		self.b.clicked.connect(self.changed)

	def setQuery(self,query):
		print("salut")

	def updateQuery(self,query):
		print("aurevoir")


class Test2Widget(AbstractQueryWidget):
	def __init__(self):
		super().__init__()

	def setQuery(self,query):
		print("salut T2")

	def updateQuery(self,query):
		print("aurevoir T2")


if __name__ == "__main__":

    path = "/tmp/cutevariant.db"
    conn = sqlite3.connect(path)



    app = QApplication(sys.argv)

    # w = MainWindow()

    # w.show()

    router = QueryRouter()

    test = TestWidget()
    test2 = Test2Widget()

    router.addWidget(test)
    router.addWidget(test2)

    q = Query(conn)

    router.setQuery(q)


    test.show()

    app.exec_()







 



