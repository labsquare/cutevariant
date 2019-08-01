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

    def __init__(self, conn = None):
        super().__init__()
        self.setColumnCount(2)
        self.items = []
        self.conn = conn

    def load(self):
        """Load columns into the model"""
        self.clear()
        # Store QStandardItem as a list to detect easily which one is checked
        self.items = list()
        categories = dict()

        # Fields is a dictionnary with (name,type,description,category) as keys
        # Create a category item and add fields as children
        for record in sql.get_fields(self.conn):

            if record["category"] != "samples":
                item = QStandardItem(record["name"])
                item.setEditable(False)
                item.setToolTip(record["description"])
                # map value type to color
                item.setIcon(FIcon(0xF70A, TYPE_COLORS[record["type"]]))
                item.setCheckable(True)
                item.setData(record)
                self.items.append(item)

                # Create category parent items
                if record["category"] not in categories.keys():
                    cat_item = QStandardItem(record["category"])
                    cat_item.setEditable(False)
                    cat_item.setIcon(FIcon(0xF645))
                    self.appendRow(cat_item)
                    categories[record["category"]] = cat_item

        # Append child to parent
        for item in self.items:
            category = item.data()["category"]
            if category != "sample":
                categories[category].appendRow(item)

        # Append samples
        sample_cat_item = QStandardItem("samples")
        sample_cat_item.setEditable(False)
        sample_cat_item.setIcon(FIcon(0xF645))
        self.appendRow(sample_cat_item)

        # Get sample names
        samples_names = (sample["name"] for sample in sql.get_samples(self.conn))

        for sample_name in samples_names:
            sample_item = QStandardItem(sample_name)
            sample_item.setCheckable(True)
            sample_item.setIcon(FIcon(0xF2E6))
            sample_item.setData({"name": ("genotype", sample_name, "GT")})
            sample_cat_item.appendRow(sample_item)
            self.items.append(sample_item)

    def set_columns(self, columns):
        """Check column name if it is in query.columns"""
        self.blockSignals(True)
        for item in self.items:
            item.setCheckState(Qt.Unchecked)
            if item.data()["name"] in columns:
                item.setCheckState(Qt.Checked)
        self.blockSignals(False)

        
      


class ColumnsWidget(QWidget):
    """Display all fields according categories"""

    column_changed = Signal(list)

    def __init__(self):
        super().__init__()

        self.setWindowTitle(self.tr("Columns"))
        self.view = QTreeView()
        self.model = ColumnsModel()
        self.view.setModel(self.model)
        # self.view.setIndentation(0)
        self.view.header().setVisible(False)
        layout = QVBoxLayout()

        layout.addWidget(self.view)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)
        self.model.itemChanged.connect(self.on_item_checked)

    @property
    def conn(self):
        return self.model.conn 

    @conn.setter
    def conn(self, conn):
        self.model.conn = conn 
        self.model.load()

    # def on_init_query(self):
    #     """Overrided"""
    #     self.model.query = self.query
    #     self.model.load()

    # def on_change_query(self):
    #     """Overrided"""
    #     #  Avoid crash with infinite loop by disconnecting the signals
    #     self.model.itemChanged.disconnect(self.on_item_checked)

    #     # check selected query fields
    #     self.model.check_query_columns()

    #     # Reconnect signals
    #     self.model.itemChanged.connect(self.on_item_checked)

    def on_item_checked(self):
        """Called when an item has been checked"""

        # Get selected columns from checked items
        selected_columns = [
            item.data()["name"]
            for item in self.model.items
            if item.checkState() == Qt.Checked
        ]


        LOGGER.debug(
            "ColumnsModel::on_item_checked: columns: %s", selected_columns
        )

        self.column_changed.emit(selected_columns)

    def set_columns(self, columns):
        self.model.set_columns(columns)
        # following line are ugly... But update doesn't work as expected ... need to explore 
        self.hide()
        self.show()
      
    


if __name__ == "__main__":
    app = QApplication(sys.argv)

    conn = sqlite3.connect("examples/test.db")


    view = ColumnsWidget()
    view.conn = conn 
    view.model.set_columns(["chr","pos"])
    view.show()


    app.exec_()