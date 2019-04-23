from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *


from .plugin import QueryPluginWidget
from cutevariant.core import Query
from cutevariant.core import sql
from cutevariant.gui.style import TYPE_COLORS
from cutevariant.gui.ficon import FIcon

class ColumnQueryModel(QStandardItemModel):

    changed = Signal()

    def __init__(self):
        super().__init__()
        self.setColumnCount(2)
        self._query = None
        self.items = []
        self._silence = False  # Don't emit signal if True

        self.itemChanged.connect(self._emit_changed)

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

        # Build tree if not 
        if self.rowCount() == 0:
            self.load()

        # check column item 
        self.check_query_columns()

    def load(self):
        self.clear()
        self.items = [] # Store QStandardItem as a list to detect easily which one is checked
        categories = set()
        samples_names = (sample["name"] for sample in sql.get_samples(self._query.conn))
        categories_items = {}

        for record in sql.get_fields(self._query.conn):
            item = QStandardItem(record["name"])
            item.setEditable(False)
            item.setToolTip(record["description"])
            # map value type to color
            item.setIcon(FIcon(0xf70a, TYPE_COLORS[record["type"]]))
            item.setCheckable(True)
            item.setData(record)

            # if record["name"] in self._query.columns:
            #     item.setCheckState(Qt.Checked)
            self.items.append(item)

            # Create category parent items 
            if record["category"] not in categories_items.keys():
                cat_item = QStandardItem(record["category"])
                cat_item.setEditable(False)
                cat_item.setIcon(FIcon(0xf645))
                self.appendRow(cat_item)
                categories_items[record["category"]] = cat_item

        # Append child to parent 
        for item in self.items:
            category = item.data()["category"]
            if category != "sample":
                categories_items[category].appendRow(item)

        # Load samples
        for sample_name in samples_names:
            sample_item = QStandardItem(sample_name)
            sample_item.setCheckable(True)
            sample_item.setIcon(FIcon(0xf2e6))
            categories_items["samples"].appendRow(sample_item)

    def check_query_columns(self):
        """
        Check column name from current query 

        """
        self._silence = True
        for item in self.items:
            item.setCheckState(Qt.Checked)
            item.setCheckState(Qt.Unchecked)
            if item.data()["name"] in self._query.columns:
                item.setCheckState(Qt.Checked)
        self._silence = False


    def _emit_changed(self):
        if not self._silence:
            self.changed.emit()


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
        self.model.changed.connect(self.changed)

    @property
    def query(self):
        """ Method override from AbstractQueryWidget"""
        return self.model.query

    @query.setter
    def query(self, query: Query):
        """ Method override from AbstractQueryWidget"""
        self.model.query = query
