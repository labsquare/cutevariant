from typing import List
import sqlite3
import json

from cutevariant.gui import plugin, FIcon, style
from cutevariant.core import sql
from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *


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

    def __init__(self, category: str = None, conn: sqlite3.Connection = None):
        """Create the model with a connection.

            conn can be None and set later

        Args:
            conn (sqlite3.Connection, optional)
        """
        super().__init__()

        # store QStandardItem which can be checked
        self._checkable_items = []
        self.conn = conn
        self.category = category

        if conn:
            self.load()

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
            Bug : What if 2 name are in different categories - Answer: no problem, this model handles the three categories individually :)
        """

        for item in self._checkable_items:
            item.setCheckState(Qt.Unchecked)
            if item.data()["name"] in fields:
                item.setCheckState(Qt.Checked)

    def load(self):
        """Load all fields from the model"""
        self.clear()
        self._checkable_items.clear()
        self.setColumnCount(2)
        self.setHorizontalHeaderLabels(["name", "description"])

        # For variants and annotations, it is easy: one row per item
        if self.category in ("variants", "annotations"):
            self.appendRow(self._load_fields(self.category))

        if self.category == "samples":

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


class FieldsEditorWidget(QWidget):
    """Displays all the fields by category
    Each category has its own tab widget, with a tableview of selectable items
    For the samples category, there TODO is a combobox that lets the user choose the appropriate sample

    Usage:

     conn = ...
     view = FieldsEditorWidget()
     view.on_open_project(conn)

    """

    ENABLE = True

    def __init__(self, parent=None):
        """"""
        super().__init__(parent)

        # Define the supported categories out of the table names of cutevariant. Modifying this list will automatically update each and every ineternal model
        categories = ["variants", "annotations", "samples"]

        self.setWindowTitle(self.tr("Columns"))

        self.views_all = {
            category: QTableView()
            if category
            in (
                "variants",
                "annotations",
            )  # Table views for variants and annotations, for samples it will be Tree view
            else QTreeView()
            for category in categories
        }  # This conditional list comprehension would need a dict to associate a category with a view...

        self.models_all = {category: FieldsModel(category) for category in categories}

        self.proxy_models_all = {}
        for category, model in self.models_all.items():
            self.proxy_models_all[category] = QSortFilterProxyModel()
            # setup proxy ( for search option )
            self.proxy_models_all[category] = QSortFilterProxyModel()
            self.proxy_models_all[category].setSourceModel(model)
            self.proxy_models_all[category].setRecursiveFilteringEnabled(True)
            # Search is case insensitive
            self.proxy_models_all[category].setFilterCaseSensitivity(Qt.CaseInsensitive)
            # Search in all columns
            self.proxy_models_all[category].setFilterKeyColumn(-1)

        self.tab_widget = QTabWidget(self)

        for view_name, view in self.views_all.items():
            self.tab_widget.addTab(view, QIcon(), view_name)
            view.setModel(self.proxy_models_all[view_name])
            view.setIconSize(QSize(16, 16))
            view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            view.setEditTriggers(QAbstractItemView.NoEditTriggers)
            view.setAlternatingRowColors(True)
            view.setSelectionBehavior(QAbstractItemView.SelectRows)
            if isinstance(view, QTreeView):
                view.header().setSectionResizeMode(QHeaderView.ResizeToContents)
                view.header().setStretchLastSection(True)
            elif isinstance(view, QTableView):
                view.setHorizontalHeader(QHeaderView(Qt.Horizontal, self))
                view.horizontalHeader().setStretchLastSection(True)
                view.horizontalHeader().setSectionResizeMode(
                    QHeaderView.ResizeToContents
                )

        self.toolbar = QToolBar(self)

        self.search_edit = QLineEdit()
        # self.view.setIndentation(0)
        # self.view.header().setVisible(False)
        layout = QVBoxLayout()

        layout.addWidget(self.toolbar)
        layout.addWidget(self.tab_widget)
        layout.addWidget(self.search_edit)

        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        # Setup toolbar
        self.toolbar.setIconSize(QSize(16, 16))
        # self.toolbar.addAction(
        #     FIcon(0xF0615), self.tr("Collapse"), self.view.collapseAll
        # )
        # self.toolbar.addAction(FIcon(0xF0616), self.tr("Expand"), self.view.expandAll)

        # setup search edit
        self.setFocusPolicy(Qt.ClickFocus)
        self.search_act = QAction(FIcon(0xF0969), self.tr("Search by keywords..."))
        self.search_act.setCheckable(True)
        self.search_act.toggled.connect(self.on_search_pressed)
        self.search_act.setShortcutContext(Qt.WidgetShortcut)
        self.search_act.setShortcut(QKeySequence.Find)
        self.toolbar.addAction(self.search_act)

        self.search_edit.setVisible(False)
        self.search_edit.setPlaceholderText(self.tr("Search by keywords... "))

        # Connect the search bar to each category there is, to filter their respective models
        for category in categories:
            self.search_edit.textChanged.connect(
                self.proxy_models_all[category].setFilterRegExp
            )

        self._is_refreshing = (
            False  # Help to avoid loop between on_refresh and on_fields_changed
        )

    def on_search_pressed(self, checked: bool):
        self.search_edit.setVisible(checked)
        self.search_edit.setFocus(Qt.MenuBarFocusReason)

    def set_connection(self, conn):
        """ Overrided from PluginWidget """

        # Update every model, one per category
        for category, model in self.models_all.items():
            model.conn = conn
            model.load()
            if category in ("variants", "annotations"):
                self.views_all[category].setRootIndex(
                    self.proxy_models_all[category].index(0, 0)
                )
            if category == "samples":
                # TODO Retrieve the selected index off of a combobox, and show in a tableview the infos about the selected sample
                # selected_sample_index = self.proxy_models_all[category].
                self.views_all[category].setRootIndex(
                    self.proxy_models_all[category].index(0, 0)
                )

    def get_selected_fields(self):
        return {
            category: model.checked_fields
            for category, model in self.models_all.items()
        }


class TestWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        file_menu = self.menuBar().addMenu(self.tr("File"))
        open_action = file_menu.addAction(self.tr("Open"))
        open_action.triggered.connect(self.open_db)
        self.view = FieldsEditorWidget()
        self.setCentralWidget(self.view)

    def open_db(self):
        db_name = QFileDialog.getOpenFileName(
            self,
            self.tr("Chose database to see its fields"),
            QDir.homePath(),
            self.tr("SQL database files (*.db)"),
        )[0]
        if db_name:
            self.conn = sql.get_sql_connection(db_name)
            self.view.set_connection(self.conn)


def main():
    import sys

    app = QApplication(sys.argv)
    # conn = sql.get_sql_connection("./examples/snpeff3_test.db")
    window = TestWindow()
    window.show()
    return app.exec_()


if __name__ == "__main__":
    exit(main())
