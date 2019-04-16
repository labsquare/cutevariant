from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *


from .plugin import QueryPluginWidget
from cutevariant.core import Query
from cutevariant.core import sql
from cutevariant.gui.ficon import FIcon

class ColumnQueryModel(QStandardItemModel):
    def __init__(self):
        super().__init__()
        self.setColumnCount(2)
        self._query = None

    @property
    def query(self):
        selected_columns = \
            [item.data()["name"] for item in self.items
             if item.checkState() == Qt.Checked]

        self._query.columns = selected_columns
        return self._query

    @query.setter
    def query(self, query: Query):
        self._query = query
        self.load()

    def load(self):
        self.clear()
        self.items = [] # Store QStandardItem as a list to detect easily which one is checked
        categories = set()
        samples = [i["name"] for i in sql.get_samples(self._query.conn)]
        # map value type to color
        colors = {
            "str": "#27A4DD",  # blue
            "bool" : "#F1646C",  # red
            "float": "#9DD5C0",  # light blue
            "int":"#FAC174",  # light yellow
        }
        categories_items = {}

        for record in sql.get_fields(self._query.conn):
            item = QStandardItem(record["name"])
            item.setEditable(False)
            item.setToolTip(record["description"])
            item.setIcon(FIcon(0xf70a, colors[record["type"]]))
            item.setCheckable(True)
            item.setData(record)

            if record["name"] in self._query.columns:
                item.setCheckState(Qt.Checked)

            self.items.append(item)
            if record["category"] not in categories_items.keys():
                cat_item = QStandardItem(record["category"])
                cat_item.setEditable(False)
                cat_item.setIcon(FIcon(0xf645))
                self.appendRow(cat_item)
                categories_items[record["category"]] = cat_item

        # Create child items 
        for item in self.items:
            category = item.data()["category"]
            if category != "sample":
                categories_items[category].appendRow(item)

        # Load samples 
        for sample in samples:
            sample_item = QStandardItem(sample)
            sample_item.setCheckable(True)
            sample_item.setIcon(FIcon(0xf2e6))
            categories_items["sample"].appendRow(sample_item)


class ColumnQueryWidget(QueryPluginWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle(self.tr("Columns"))
        self.view = QTreeView()
        self.model = ColumnQueryModel()
        self.view.setModel(self.model)
        #self.view.setIndentation(0)
        self.view.header().setVisible(False)
        layout = QVBoxLayout()

        layout.addWidget(self.view)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)
        self.model.itemChanged.connect(self.changed)

    @property
    def query(self):
        """ Method override from AbstractQueryWidget"""
        return self.model.query

    @query.setter
    def query(self, query: Query):
        """ Method override from AbstractQueryWidget"""
        self.model.query = query
