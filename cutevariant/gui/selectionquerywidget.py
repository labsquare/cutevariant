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
        self.query = query
        self.refresh()

    def refresh(self):
        self.clear()
        for record in sql.get_selections(self.query.conn):
            name_item = QStandardItem(record["name"])
            count_item = QStandardItem(str(record["count"]))
            self.appendRow([name_item, count_item])

    def save_current_query(self, name):
        sql.create_selection_from_sql(self.query.conn, name, self.query.sql())
        self.refresh()


class SelectionQueryWidget(AbstractQueryWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Selections")
        self.view = QTreeView()
        self.model = SelectionQueryModel()
        self.view.setModel(self.model)

        layout = QVBoxLayout()

        layout.addWidget(self.view)
        layout.setContentsMargins(0,0,0,0)
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

    def save_current_query(self):

        name, success = QInputDialog.getText(
            self, "type a name for selection", "Selection name:", QLineEdit.Normal
        )

        if success:
            self.model.save_current_query(name)
