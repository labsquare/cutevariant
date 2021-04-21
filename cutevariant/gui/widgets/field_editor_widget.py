from typing import List
import sqlite3
from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *


from cutevariant.gui import style
from cutevariant.gui import FIcon
from cutevariant.core import sql


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

        # For samples table, it is a bit more complex
        elif self.category == "samples":

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


class FieldsWidget(QWidget):
    """
    This widget shows all the field names of a given category (either variants, annotation, or samples)
    """

    def __init__(self, category, parent=None):
        super().__init__(parent)
        self.category = category

        self.table_view = QTableView()
        self.model = FieldsModel(category)
        self.proxy_model = QSortFilterProxyModel()
        self.proxy_model.setSourceModel(self.model)
        self.table_view.setModel(self.proxy_model)

        self.table_view.setHorizontalHeader(QHeaderView(Qt.Horizontal, self))
        self.table_view.horizontalHeader().setStretchLastSection(True)
        self.table_view.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeToContents
        )

        self.table_view.setIconSize(QSize(16, 16))
        self.table_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.table_view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_view.setAlternatingRowColors(True)
        self.table_view.setSelectionBehavior(QAbstractItemView.SelectRows)

        self.table_view.setRootIndex(self.proxy_model.index(0, 0, QModelIndex()))

        self.proxy_model.setRecursiveFilteringEnabled(True)
        # Search is case insensitive
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseInsensitive)
        # Search in all columns
        self.proxy_model.setFilterKeyColumn(-1)

        self.hlayout = QHBoxLayout(self)
        self.hlayout.addWidget(self.table_view)

        # ----------------------------------------
        # # For the samples category, split up the widget in two
        # if self.category == "samples":
        #     self.sample_selection_view = QListView(self)
        #     self.hlayout.insertWidget(0, self.sample_selection_view)

    def set_connection(self, conn):

        self.model.conn = conn
        self.model.load()

        # ----------------New idea to display the samples as two separate views.
        # ----------------For now, doesn't work
        # ----------------because of a weird error : Invalid index when trying to setup a selction model...
        # if self.category == "samples":
        #     self.sample_selection_view.setModel(self.proxy_model)
        #     self.sample_selection_view.setRootIndex(
        #         self.proxy_model.index(0, 0, QModelIndex())
        #     )
        #     self.sample_selection_view.selectionModel().setModel(self.proxy_model)
        #     self.sample_selection_view.selectionModel().currentChanged.connect(
        #         lambda cur, prev: self.table_view.setRootIndex(
        #             self.proxy_model.index(0, 0, cur)
        #         )
        #     )
        #     return

        self.table_view.setRootIndex(self.proxy_model.index(0, 0))


class SamplesWidget(QWidget):
    """docstring for ClassName"""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.view = QTreeView()
        self.model = FieldsModel("samples")
        self.proxy_model = QSortFilterProxyModel()
        self.proxy_model.setSourceModel(self.model)
        self.view.setModel(self.proxy_model)
        self.vlayout = QVBoxLayout(self)
        self.vlayout.addWidget(self.view)
        self.view.header().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.view.header().setStretchLastSection(True)


class FieldsEditorWidget(QWidget):
    """Displays all the fields by category
    Each category has its own tab widget, with a tableview of selectable items
    For the samples category, there TODO is a combobox that lets the user choose the appropriate sample

    Usage:

     conn = ...
     view = FieldsEditorWidget()
     view.on_open_project(conn)

    """

    def __init__(self, parent=None):
        """"""
        super().__init__(parent)

        self.setWindowTitle(self.tr("Columns"))

        self.widgets = {
            "variants": FieldsWidget("variants"),
            "annotations": FieldsWidget("annotations"),
            "samples": FieldsWidget("samples"),
        }

        self.tab_widget = QTabWidget(self)

        for view_name, widget in self.widgets.items():

            self.tab_widget.addTab(widget, widget.windowIcon(), view_name)

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

    def on_search_pressed(self, checked: bool):
        self.search_edit.setVisible(checked)
        self.search_edit.setFocus(Qt.MenuBarFocusReason)

    def set_connection(self, conn):
        # Update every model, one per category
        for name, widget in self.widgets.items():
            widget.set_connection(conn)

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
