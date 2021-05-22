from functools import lru_cache
import sqlite3

import json

from PySide2.QtCore import (
    QAbstractTableModel,
    QModelIndex,
    Qt,
    Signal,
    QAbstractListModel,
    QObject,
    QSize,
    QSortFilterProxyModel,
)
from PySide2.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
    QTabWidget,
    QTableView,
    QHeaderView,
)
from PySide2.QtGui import QStandardItemModel, QStandardItem, QFont

from cutevariant.gui.plugin import PluginWidget
from cutevariant.core import sql
from cutevariant.gui.widgets import SearchableTableWidget
import cutevariant.commons as cm

from cutevariant.gui import plugin, FIcon, style

LOGGER = cm.logger()


def load_fields(conn):
    """
    Returns a dict with field info for each category.
    Example result:
    {
        "variants":
        {
            "chr":{"type":"str","description":{"The chromosome the variant was found on"}},
            "pos":{...}
        },
        "annotations":
        {
            "ann.gene":{"type":"str","description":"Name of the gene where the variant is"}},
            "ann.impact":{...}
        },
        "samples":
        {
            "samples.boby.gt":{"type":"int","description":{"Genotype for this sample (0:hom. for ref, 1: het for alt, 2:hom for alt)}}
            "samples.boby.dp":{...}
        }
    }
    """

    results = {"variants": {}, "annotations": {}, "samples": {}}

    samples = [sample["name"] for sample in sql.get_samples(conn)]

    for field in sql.get_fields(conn):

        if field["category"] == "variants":
            name = field["name"]
            results["variants"][name] = {
                "type": field["type"],
                "description": field["description"],
            }

        if field["category"] == "annotations":
            name = field["name"]
            results["annotations"][f"ann.{name}"] = {
                "type": field["type"],
                "description": field["description"],
            }

        if field["category"] == "samples":
            name = field["name"]
            for sample in samples:
                results["samples"][f"samples.{sample}.{name}"] = {
                    "type": field["type"],
                    "description": field["description"],
                }

    return results


class FieldsModel(QStandardItemModel):
    """
    Standard key,value model (2 columns) with field name and its respective description
    """

    fields_loaded = Signal()

    def __init__(
        self, conn: sqlite3.Connection = None, category="variants", parent=None
    ):
        super().__init__(0, 2, parent)
        self._checkable_items = []
        self.conn = conn
        self._category = category

    @property
    def conn(self):
        return self._conn

    @conn.setter
    def conn(self, conn):
        self._conn = conn
        if self._conn:
            self.load()
        else:
            self.clear()

    def load(self):
        """Load all fields from the model"""

        # Don't forget to reset the model
        self.clear()

        # Clear checkable items as well, the list may contain selected items from another project...
        self._checkable_items.clear()

        self.setColumnCount(2)
        self.setHorizontalHeaderLabels(["name", "description"])

        if self.conn:
            fields = load_fields(self.conn).get(self._category, None)
            if not fields:
                LOGGER.warning("Cannot load field category %s", self._category)
            else:
                for field in fields:
                    field_name = field
                    if self._category == "annotations":
                        # Remove the ann. prefix (4 characters)
                        field_name = field_name[4:]
                    if self._category == "samples":
                        # Remove the samples. prefix (8 characters)
                        field_name = field_name[8:]

                    field_desc = fields[field]["description"]

                    field_name_item = QStandardItem(field_name)
                    field_name_item.setCheckable(True)
                    font = QFont()
                    font.setBold(True)
                    field_name_item.setFont(font)
                    field_type = style.FIELD_TYPE.get(fields[field]["type"])
                    field_name_item.setIcon(
                        FIcon(field_type["icon"], "white", field_type["color"])
                    )

                    self._checkable_items.append(field_name_item)
                    field_name_item.setData(
                        {
                            "name": field,
                            "type": fields[field]["type"],
                            "description": fields[field]["description"],
                        }
                    )

                    descr_item = QStandardItem(field_desc)
                    descr_item.setToolTip(fields[field]["description"])

                    self.appendRow([field_name_item, descr_item])
                    self.fields_loaded.emit()

    def to_json(self, filename: str):
        """Serialize checked fields to a json file

        Args:
            filename (str): a json filename

        TODO: Rename to 'to_json'
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


class FieldsWidget(QWidget):

    fields_changed = Signal()

    def __init__(self, conn: sqlite3.Connection = None, parent=None):
        super().__init__(parent)
        self.tab_widget = QTabWidget(self)

        self.views = []

        # Create the variants widget (the view and its associated filter model)
        self.add_view(conn, "variants")

        # Create the annotations widget (the view and its associated filter model)
        self.add_view(conn, "annotations")

        # Create the samples widget (the view and its associated filter model)
        self.add_view(conn, "samples")

        layout = QVBoxLayout(self)
        layout.addWidget(self.tab_widget)
        layout.setContentsMargins(0, 0, 0, 0)

        self.conn = conn

    def add_view(self, conn, category):
        model = FieldsModel(conn, category)
        view = QTableView()
        proxy = QSortFilterProxyModel()
        proxy.setSourceModel(model)

        view.setModel(proxy)
        view.horizontalHeader().setStretchLastSection(True)
        view.setIconSize(QSize(16, 16))
        view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        view.setSelectionMode(QAbstractItemView.SingleSelection)
        view.setSelectionBehavior(QAbstractItemView.SelectRows)
        view.setAlternatingRowColors(True)
        view.setWordWrap(True)
        view.verticalHeader().hide()
        view.setSortingEnabled(True)

        proxy.setRecursiveFilteringEnabled(True)
        proxy.setFilterCaseSensitivity(Qt.CaseInsensitive)
        proxy.setFilterKeyColumn(-1)

        model.itemChanged.connect(lambda: self.fields_changed.emit())

        self.views.append(
            {"view": view, "proxy": proxy, "model": model, "name": category}
        )
        self.tab_widget.addTab(
            view, FIcon(style.FIELD_CATEGORY.get(category, None)["icon"]), category
        )

    def update_filter(self, text: str):
        """
        Callback for when the search bar is updated (filter the three models)
        """
        for index, view in enumerate(self.views):
            view["proxy"].setFilterRole(Qt.DisplayRole)
            view["proxy"].setFilterRegExp(text)
            count = view["proxy"].rowCount()
            name = view["name"]
            self.tab_widget.setTabText(index, f"{name} ({count})")

    def show_checked_only(self, active=False):

        for index, view in enumerate(self.views):
            view["proxy"].setFilterRole(Qt.CheckStateRole)
            view["proxy"].setFilterKeyColumn(0)
            # Checked = "2" / Unchecked = "0" / All : ""
            is_checked_str = "2" if active else ""
            print(is_checked_str)
            view["proxy"].setFilterFixedString(is_checked_str)
            count = view["proxy"].rowCount()
            name = view["name"]
            self.tab_widget.setTabText(index, f"{name} ({count})")

    @property
    def checked_fields(self) -> list:
        """Return checked fields

        Returns:
            List[str] : list of checked fields
        """
        result = []
        for view in self.views:
            result += view["model"].checked_fields
        return result

    @checked_fields.setter
    def checked_fields(self, fields: list):
        """Check fields according name

        Arguments:
            columns (List[str]):
        """
        for view in self.views:
            view["model"].checked_fields = fields

    @property
    def conn(self):
        return self._conn

    @conn.setter
    def conn(self, conn):
        self._conn = conn
        for index, view in enumerate(self.views):
            model = view["model"]
            name = view["name"]
            model.conn = conn
            self.tab_widget.setTabText(index, f"{name} ({model.rowCount()})")
            if conn:
                view["view"].horizontalHeader().setSectionResizeMode(
                    0, QHeaderView.ResizeToContents
                )


class CategoricalFieldsModel(QAbstractListModel):
    def __init__(self, parent: QObject) -> None:
        super().__init__(parent)
        self._raw_data = []

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._raw_data)

    def data(self, index: QModelIndex, role: int):
        if not index.isValid():
            return

        if index.column() != 0:
            return

        if index.row() < 0 or index.row() >= self.rowCount():
            return

        if role == Qt.DisplayRole:
            return self._raw_data[index.row()]

    def clear(self):
        self._set_raw_data([])

    def load(self, conn: sqlite3.Connection, category: str):
        """Loads every field in selected category from database conn

        Args:
            conn (sqlite3.Connection): Access to cutevariant's project database
            category (str): One of ["variants","annotations","samples"]
        """
        self._set_raw_data(
            [
                field["name"]
                for field in sql.get_field_by_category(conn, category)
                if field["type"] in ("int", "bool", "str")
            ]
        )

    def _set_raw_data(self, raw_data: list):
        self.beginResetModel()
        self._raw_data = raw_data
        self.endResetModel()


class GroupbyModel(QAbstractTableModel):
    def __init__(self, parent: QObject) -> None:
        super().__init__(parent)
        self._raw_data = []
        self._field_name = ""

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._raw_data)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 2

    def headerData(self, section: int, orientation: Qt.Orientation, role: int):

        if section not in (0, 1):
            return

        if orientation != Qt.Horizontal:
            return

        if role == Qt.DisplayRole:
            return ["Value", "Count"][section]

    def data(self, index: QModelIndex, role: int):
        if not index.isValid():
            return

        if index.column() not in (0, 1):
            return

        if index.row() < 0 or index.row() >= self.rowCount():
            return

        if role == Qt.DisplayRole:
            cols = {0: self._field_name, 1: "count"}
            return self._raw_data[index.row()][cols[index.column()]]

    def clear(self):
        self._set_raw_data([])

    def load(
        self,
        conn: sqlite3.Connection,
        field_name: str,
        fields: list,
        source="variants",
        filters={},
        order_desc=True,
        order_by_count=True,
        limit=50,
        offset=0,
    ):
        """Counts unique values inside field_name

        Args:
            conn (sqlite3.Connection): Access to cutevariant's project database
            field_name (str): The field you want the number of unique values of
        """
        self._set_raw_data(
            list(sql.get_variant_as_group(conn, field_name, fields, source, filters))
        )
        self._field_name = field_name

    def _set_raw_data(self, raw_data: list):
        self.beginResetModel()
        self._raw_data = raw_data
        self.endResetModel()


class GroupByViewWidget(PluginWidget):
    """Plugin to show, for any categorical field selected, the count of each unique value."""

    ENABLE = True

    REFRESH_STATE_DATA = {"fields", "filters", "source"}

    def __init__(self, parent=None, conn=None):
        super().__init__()
        self.conn = conn
        self.field_select_combo = QComboBox(self)

        self.view = SearchableTableWidget(self)

        self.groupby_model = GroupbyModel(self)

        self.view.proxy.setSourceModel(self.groupby_model)
        self.view.tableview.setSelectionMode(QAbstractItemView.SingleSelection)
        self.view.tableview.setSelectionBehavior(QAbstractItemView.SelectRows)

        self.setWindowTitle(self.tr("Group By"))

        layout = QVBoxLayout(self)
        layout.addWidget(self.field_select_combo)
        layout.addWidget(self.view)

        self.field_select_combo.currentTextChanged.connect(self._load_groupby)

        self._order_desc = True
        self._order_by_count = True
        self._limit = 50
        self._offset = 0

    def on_open_project(self, conn):
        self.conn = conn
        self.on_refresh()

    def on_refresh(self):
        """Overrided from PluginWidget"""
        # Save default data with current query attributes
        # See load(), we use this attr to restore fields after grouping

        # Load ui
        self.load()

    def load(self):
        """Load view
        Called by on_refresh
        """
        if self.conn:
            self.field_select_combo.clear()
            self.field_select_combo.addItems(self.mainwindow.get_state_data("fields"))
            self._load_groupby()
        else:
            self.groupby_model.clear()

    def _load_groupby(self):
        if self.conn:
            self.groupby_model.load(
                self.conn,
                self.field_select_combo.currentText(),
                self.mainwindow.get_state_data("fields"),
                self.mainwindow.get_state_data("source"),
                self.mainwindow.get_state_data("filters"),
                self._order_desc,
            )


if __name__ == "__main__":
    import sys
    from PySide2.QtWidgets import QApplication

    app = QApplication(sys.argv)

    conn = sql.get_sql_connection("test.db")

    w = GroupByViewWidget()
    w.conn = conn

    w.show()

    app.exec_()
