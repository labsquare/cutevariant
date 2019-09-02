"""Plugin to view all fields available for variants, annotations and samples

SelectionQueryWidget class is seen by the user and uses ColumnsModel class
as a model that handles records from the database.
"""
import sys
import sqlite3

# Qt imports
from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *

# Custom imports
from cutevariant.core import sql
from cutevariant.gui.style import TYPE_COLORS
from cutevariant.gui.ficon import FIcon
from cutevariant.commons import logger

LOGGER = logger()


class ColumnsModel(QStandardItemModel):
    """Model to store all fields available for variants, annotations and samples"""

    def __init__(self, conn=None):
        super().__init__()
        self.checkable_items = []
        self.conn = conn
        
    def columnCount(self, index = QModelIndex()):
        return 1

    def headerData(self, section,orientation, role):
        
        if role != Qt.DisplayRole:
            return None 

        if orientation == Qt.Horizontal:
            if section == 0:
                return "Name"
            if section == 1:
                return "Description" 
        
        return None


    @property
    def columns(self):
        """Return checked columns
        
        Returns:
            list -- list of columns
        """
        selected_columns = []
        for item in self.checkable_items:
            if item.checkState() == Qt.Checked:
                selected_columns.append(item.data()["name"])
        return selected_columns

    @columns.setter
    def columns(self, columns):
        """Check items which name is in columns
        
        Arguments:
            columns {list} -- list of columns
        """
        self.blockSignals(True)
        for item in self.checkable_items:
            item.setCheckState(Qt.Unchecked)
            if item.data()["name"] in columns:
                item.setCheckState(Qt.Checked)
        self.blockSignals(False)

    def load(self):
        """Load all columns avaible into the model 
        """
        self.clear()
        self.checkable_items.clear()

        self.appendRow(self.load_fields("variants"))
        self.appendRow(self.load_fields("annotations"))

        samples_items = QStandardItem("samples")
        samples_items.setIcon(FIcon(0xf00e))
        font = QFont()
        font.setBold(True)
        samples_items.setFont(font)

        for sample in sql.get_samples(self.conn):
            sample_item = self.load_fields("samples", parent_name = sample["name"])
            sample_item.setText(sample["name"])
            samples_items.appendRow(sample_item)



        self.appendRow(samples_items)


    def load_fields(self, category, parent_name = None):
        root_item = QStandardItem(category)
        root_item.setColumnCount(2)
        root_item.setIcon(FIcon(0Xf24b))
        font = QFont()
        font.setBold(True)
        root_item.setFont(font)

        for field in sql.get_field_by_category(self.conn,category):
            item1 = QStandardItem(field["name"])
            item2 = QStandardItem(field["description"])
            item1.setCheckable(True)
            root_item.appendRow([item1, item2])
            self.checkable_items.append(item1)
            
            if category == "samples":
                item1.setData({"name": ("genotype", parent_name, field["name"])})
            else:
                item1.setData(field)
        
        return root_item




class ColumnsWidget(QWidget):
    """Display all fields according categories

    Usage: 

     view = ColumnsWidget(conn)
     view.columns = ["chr","pos"]
    
    """

    changed = Signal()

    def __init__(self, parent=None):
        super().__init__()

        self.setWindowTitle(self.tr("Columns"))
        self.view = QTreeView()
        self.model = ColumnsModel(None)
        self.view.setModel(self.model)
        self.view.setIconSize(QSize(20,20))
        
        # self.view.setIndentation(0)
        #self.view.header().setVisible(False)
        layout = QVBoxLayout()

        layout.addWidget(self.view)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)
        self.model.itemChanged.connect(self.changed)

    @property
    def conn(self):
        return self.model.conn

    @conn.setter
    def conn(self, conn):
        self.model.conn = conn
        if conn:
            self.model.load()

    @property
    def columns(self):
        return self.model.columns

    @columns.setter
    def columns(self, columns):
        self.model.columns = columns

    def load(self):
        self.model.load()


if __name__ == "__main__":
    app = QApplication(sys.argv)

    conn = sqlite3.connect("examples/test.db")

    view = ColumnsWidget()
    view.conn = conn
    view.model.columns = ["chr", "pos"]

    view.changed.connect(lambda : print(view.columns))

    view.show()

    app.exec_()
