from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *


from .plugin import QueryPluginWidget
from cutevariant.core import Query
from cutevariant.core import sql


class SelectionQueryModel(QStandardItemModel):
    def __init__(self):
        super().__init__()
        self.setColumnCount(2)
        self._query = None

    @property
    def query(self):
        return self._query

    @query.setter
    def query(self, query: Query):
        self._query = query
        self.refresh()

    def refresh(self):
        self.clear()
        for record in sql.get_selections(self._query.conn):
            name_item = QStandardItem(record["name"])
            count_item = QStandardItem(str(record["count"]))
            self.appendRow([name_item, count_item])

    def save_current_query(self, name):
        self.query.create_selection(name)
        self.refresh()


class SelectionQueryWidget(QueryPluginWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle(self.tr("Selections"))
        self.view = QTreeView()
        self.model = SelectionQueryModel()
        self.view.setModel(self.model)

        layout = QVBoxLayout()

        layout.addWidget(self.view)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        self.view.selectionModel().currentRowChanged.connect(self.changed)

    @property
    def query(self):
        """ Method override from AbstractQueryWidget"""

        item = self.model.item(self.view.selectionModel().currentIndex().row())

        query = self.model.query
        query.selection = item.text()

        return query

    @query.setter
    def query(self, query: Query):
        """ Method override from AbstractQueryWidget"""
        self.model.query = query

    def save_current_query(self):

        name, success = QInputDialog.getText(
            self, "type a name for selection", "Selection name:", QLineEdit.Normal
        )

        if success:
            self.model.save_current_query(name)
