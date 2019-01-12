from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *


from .abstractquerywidget import AbstractQueryWidget
from cutevariant.core import Query
from cutevariant.core import sql


class SelectionQueryModel(QStandardItemModel):
    def __init__(self):
        super().__init__()
        self.setColumnCount(2)

    def setQuery(self, query: Query):
         self.clear()
         self.query = query

         for record in sql.get_selections(query.conn):
            name_item = QStandardItem(record["name"])
            count_item = QStandardItem(str(record["count"]))

            self.appendRow([name_item, count_item])





class SelectionQueryWidget(AbstractQueryWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Selections")
        self.view = QTreeView()
        self.model = SelectionQueryModel()
        self.view.setModel(self.model)

        layout = QVBoxLayout()

        layout.addWidget(self.view)
        self.setLayout(layout)

        self.view.selectionModel().currentRowChanged.connect(self.changed)



    def setQuery(self, query: Query):
        """ Method override from AbstractQueryWidget"""
        self.model.setQuery(query)

    def getQuery(self):
        """ Method override from AbstractQueryWidget"""

        item = self.model.item(self.view.selectionModel().currentIndex().row())

        query = self.model.query 
        query.selection = item.text()

        return query
