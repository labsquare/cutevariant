from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *


from .plugin import QueryPluginWidget
from cutevariant.core import Query
from cutevariant.core import sql
from cutevariant.gui.style import TYPE_COLORS
from cutevariant.gui.ficon import FIcon

class ColumnQueryModel(QStandardItemModel):
    """
    This model store all fields avaible for variant, annotation and samples 

    """

    def __init__(self):
        super().__init__()
        self.setColumnCount(2)
        self.query = None
        self.items = []


    def load(self):
        """ Load columns into the model """ 
        self.clear()
        self.items = [] # Store QStandardItem as a list to detect easily which one is checked
        categories = {}

        # get sample names 
        samples_names = (sample["name"] for sample in sql.get_samples(self.query.conn))
        
        # fields is a dictionnary with (name,type,description,category)
        # Create a category item and add fields as children
        for record in sql.get_fields(self.query.conn):

            if record["category"] != "samples":
                item = QStandardItem(record["name"])
                item.setEditable(False)
                item.setToolTip(record["description"])
                # map value type to color
                item.setIcon(FIcon(0xf70a, TYPE_COLORS[record["type"]]))
                item.setCheckable(True)
                item.setData(record)
                self.items.append(item)

                # Create category parent items 
                if record["category"] not in categories.keys():
                    cat_item = QStandardItem(record["category"])
                    cat_item.setEditable(False)
                    cat_item.setIcon(FIcon(0xf645))
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
        sample_cat_item.setIcon(FIcon(0xf645))
        self.appendRow(sample_cat_item)

        for sample_name in samples_names:
            sample_item = QStandardItem(sample_name)
            sample_item.setCheckable(True)
            sample_item.setIcon(FIcon(0xf2e6))
            sample_item.setData({"name":("genotype", sample_name, "GT")})
            sample_cat_item.appendRow(sample_item)
            self.items.append(sample_item)


    def check_query_columns(self):
        """
        Check column name if it is in query.columns
        """
        for item in self.items:
            item.setCheckState(Qt.Unchecked)
            if item.data()["name"] in self.query.columns:
                item.setCheckState(Qt.Checked)


class ColumnQueryWidget(QueryPluginWidget):
    """
    This QueryPluginWidget display all fields according categories
    """
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
        self.model.itemChanged.connect(self.on_item_checked)



    def on_init_query(self):
        """ overrided """ 
        self.model.query = self.query
        self.model.load()

    def on_change_query(self):
        """ Overrided """
        # Avoid crash with infinite loop by disconnecting the signals
        self.model.itemChanged.disconnect(self.on_item_checked)

        # check selected query fields
        self.model.check_query_columns()

        # Reconnect signals 
        self.model.itemChanged.connect(self.on_item_checked)

        
    def on_item_checked(self):
        """ This method is called when an item has been checked """ 

        # get selected columns from checked items 
        selected_columns = \
            [item.data()["name"] for item in self.model.items
             if item.checkState() == Qt.Checked]



        # Update query with selected columns 
        self.query.columns = selected_columns

        print(self.query.columns)


        # Signal other widget that query has changed 
        self.query_changed.emit()
