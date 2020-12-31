from cutevariant.gui import plugin, FIcon, style
from cutevariant.core import sql
from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *

from typing import List
import sqlite3
import json


class FieldsModel(QStandardItemModel):
    """Model to display all fields from databases into 3 groups (variants, annotation, samples)
    Fields are checkable and can be set using setter/getter checked_fields .

    Examples: 
        
        from cutevariant.core import sql 
        conn = sql.get_connectionn("project.db")

        model = FieldsModel(conn)
        view = QTreeView()
        view.setModel(model)
        
        model.checked_fields = ["chr","pos","ref"]
        model.load() 


    Attributes:
        conn (sqlite3.Connection)

    Todo : 
        Possible bug with duplicate name in different categories.
        e.g: variants.gene and annotations.gene    
    
    """

    def __init__(self, conn: sqlite3.Connection = None):
        """Create the model with a connection.
            
            conn can be None and set later 
        
        Args:
            conn (sqlite3.Connection, optional)
        """
        super().__init__()

        # store QStandardItem which can be checked
        self._checkable_items = []
        self.conn = conn

    @property
    def checked_fields(self) -> List[str]:
        """Return checked fields
        
        Returns:
            List[str] : list of checked fields
        """
        selected_fields = []
        for item in self._checkable_items:
            if item.checkState() == Qt.Checked:
                selected_fields.append(item.data()["name"])
        return selected_fields

    @checked_fields.setter
    def checked_fields(self, fields: List[str]):
        """Check fields according name 
        
        Arguments:
            columns (List[str]): 

        Todo: 
            Bug : What if 2 name are in different categories 
        """

        for item in self._checkable_items:
            item.setCheckState(Qt.Unchecked)
            if item.data()["name"] in fields:
                item.setCheckState(Qt.Checked)

    def load(self):
        """Load all fields from the model
        """
        self.clear()
        self._checkable_items.clear()
        self.setColumnCount(2)
        self.setHorizontalHeaderLabels(["name", "description"])

        #  Load fields from variant categories
        self.appendRow(self._load_fields("variants"))
        #  Load fields from annotations categories
        self.appendRow(self._load_fields("annotations"))
        # Create and load fields from samples categories
        samples_items = QStandardItem("samples")
        samples_items.setIcon(FIcon(0xF0B9C))
        font = QFont()

        samples_items.setFont(font)
        for sample in sql.get_samples(self.conn):
            sample_item = self._load_fields("samples", parent_name=sample["name"])
            sample_item.setText(sample["name"])
            sample_item.setIcon(FIcon(0xF0B9C))
            samples_items.appendRow(sample_item)

        self.appendRow(samples_items)

    def _load_fields(self, category: str, parent_name: str = None) -> QStandardItem:
        """Load fields from database and create a QStandardItem
        
        Args:
            category (str): category name : eg. variants / annotations / samples
            parent_name (str, optional): name of the parent item 
        
        Returns:
            QStandardItem
        """
        root_item = QStandardItem(category)
        root_item.setColumnCount(2)
        root_item.setIcon(FIcon(0xF0256))
        font = QFont()
        root_item.setFont(font)

        for field in sql.get_field_by_category(self.conn, category):
            field_name = QStandardItem(field["name"])
            descr = QStandardItem(field["description"])
            descr.setToolTip(field["description"])

            field_name.setCheckable(True)

            field_type = style.FIELD_TYPE.get(field["type"])
            field_name.setIcon(FIcon(field_type["icon"], "white", field_type["color"]))

            root_item.appendRow([field_name, descr])
            self._checkable_items.append(field_name)

            if category == "samples":
                field_name.setData({"name": ("sample", parent_name, field["name"])})
            else:
                field_name.setData(field)

        return root_item

    def to_file(self, filename: str):
        """Serialize checked fields to a json file
        
        Args:
            filename (str): a json filename
        """
        with open(filename, "w") as outfile:
            obj = {"checked_fields": self.checked_fields}
            json.dump(obj, outfile)

    def from_file(self, filename: str):
        """Unserialize checked fields from a json file
        
        Args:
            filename (str): a json filename
        """
        with open(filename, "r") as infile:
            obj = json.load(infile)
            self.checked_fields = obj.get("checked_fields", [])


class FieldsEditorWidget(plugin.PluginWidget):
    """Display all fields according categorie

    Usage:

     view = FieldsWidget
     (conn)
     view.columns = ["chr","pos"]

    """

    ENABLE = True

    def __init__(self, conn=None, parent=None):
        super().__init__(parent)

        self.setWindowTitle(self.tr("Columns"))
        self.view = QTreeView(self)
        self.toolbar = QToolBar(self)
        # conn is always None here but initialized in on_open_project()
        self.model = FieldsModel(conn)

        # setup proxy ( for search option )
        self.proxy_model = QSortFilterProxyModel()
        self.proxy_model.setSourceModel(self.model)
        self.proxy_model.setRecursiveFilteringEnabled(True)
        # Search is case insensitive
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseInsensitive)
        # Search in all columns
        self.proxy_model.setFilterKeyColumn(-1)

        self.view.setModel(self.proxy_model)
        self.view.setIconSize(QSize(16, 16))
        self.view.header().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.search_edit = QLineEdit()
        # self.view.setIndentation(0)
        self.view.header().setVisible(False)
        layout = QVBoxLayout()

        layout.addWidget(self.toolbar)
        layout.addWidget(self.view)
        layout.addWidget(self.search_edit)

        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)
        self.model.itemChanged.connect(self.on_fields_changed)

        # Setup toolbar
        self.toolbar.setIconSize(QSize(16, 16))
        self.toolbar.addAction(
            FIcon(0xF0615), self.tr("Collapse"), self.view.collapseAll
        )
        self.toolbar.addAction(FIcon(0xF0616), self.tr("Expand"), self.view.expandAll)

        # setup search edit
        self.setFocusPolicy(Qt.ClickFocus)
        self.search_act = QAction(FIcon(0xF0969), self.tr("Search by keywords..."))
        self.search_act.setCheckable(True)
        self.search_act.toggled.connect(self.on_search_pressed)
        self.search_act.setShortcutContext(Qt.WidgetShortcut)
        self.search_act.setShortcut(QKeySequence.Find)
        self.toolbar.addAction(self.search_act)

        self.view.addAction(self.search_act)

        self.search_edit.setVisible(False)
        self.search_edit.setPlaceholderText(self.tr("Search by keywords... "))

        self.search_edit.textChanged.connect(self.proxy_model.setFilterRegExp)

        self._is_refreshing = (
            False  # Help to avoid loop between on_refresh and on_fields_changed
        )

    def on_search_pressed(self, checked: bool):
        self.search_edit.setVisible(checked)
        self.search_edit.setFocus(Qt.MenuBarFocusReason)

    def on_open_project(self, conn):
        """ Overrided from PluginWidget """
        self.model.conn = conn
        self.model.load()
        self.on_refresh()

    def on_refresh(self):
        """ overrided from PluginWidget """
        self._is_refreshing = True
        self.model.checked_fields = self.mainwindow.state.fields
        self._is_refreshing = False

    def on_fields_changed(self):

        if self.mainwindow is None or self._is_refreshing:
            return

        self.mainwindow.state.fields = self.model.checked_fields
        self.mainwindow.refresh_plugins(sender=self)


if __name__ == "__main__":
    import sys
    from cutevariant.core.importer import import_reader
    from cutevariant.core.reader import FakeReader

    app = QApplication(sys.argv)

    conn = sql.get_sql_connection(":memory:")
    import_reader(conn, FakeReader())
    # import_file(conn, "examples/test.snpeff.vcf")

    view = FieldsEditorWidget()

    view.conn = conn
    view.fields = ["chr", "pos"]

    # view.changed.connect(lambda : print(view.columns))

    view.show()

    app.exec_()
