from functools import lru_cache
import sqlite3

import json
from tests.gui.test_plugins import MainWindow

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
    QMessageBox,
    QVBoxLayout,
    QWidget,
    QTabWidget,
    QTableView,
    QHeaderView,
)
from PySide2.QtGui import QIcon, QStandardItemModel, QStandardItem, QFont

from cutevariant.gui.plugin import PluginWidget
from cutevariant.core import sql
from cutevariant.gui.sql_thread import SqlThread
from cutevariant.gui.widgets import SearchableTableWidget
import cutevariant.commons as cm

from cutevariant.gui import plugin, FIcon, style

LOGGER = cm.logger()


class GroupbyModel(QAbstractTableModel):

    groupby_started = Signal()
    groubpby_finished = Signal()
    groupby_error = Signal()

    def __init__(self, parent: QObject = None, conn: sqlite3.Connection = None) -> None:
        super().__init__(parent)
        self._raw_data = []
        self._field_name = ""
        self._conn = conn
        self.load_groupby_thread = SqlThread(self._conn)
        self.load_groupby_thread.started.connect(self.groupby_started)
        self.load_groupby_thread.result_ready.connect(self.groubpby_finished)
        self.load_groupby_thread.result_ready.connect(self._on_data_available)
        self.load_groupby_thread.error.connect(self._on_error)

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

    def set_conn(self, conn: sqlite3.Connection):
        self._conn = conn
        self.load_groupby_thread.conn = self._conn

    def load(
        self,
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
        self._field_name = field_name
        groupby_func = lambda conn: sql.get_variant_as_group(
            conn, field_name, fields, source, filters
        )
        if self._conn:
            self.load_groupby_thread.start_function(
                lambda conn: list(groupby_func(conn))
            )

    def _on_data_available(self):
        self._set_raw_data(self.load_groupby_thread.results)

    def _on_load_finished(self):
        self.groubpby_finished.emit()

    def _on_error(self):
        QMessageBox.critical(
            None,
            self.tr("Error!"),
            self.tr(f"Cannot load field {self._field_name}"),
        )
        self.groupby_error.emit()

    def _set_raw_data(self, raw_data: list):
        if self._field_name not in raw_data[0]:
            self.clear()
            return
        self.beginResetModel()
        self._raw_data = raw_data
        self.endResetModel()

    def get_field_name(self):
        return self._field_name


class GroupbyTable(SearchableTableWidget):
    def __init__(self, conn=None, parent=None):
        super().__init__(parent=parent)
        self.conn = conn
        self.groupby_model = GroupbyModel(self)
        self.proxy.setSourceModel(self.groupby_model)
        self.tableview.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tableview.setSelectionBehavior(QAbstractItemView.SelectRows)

        self.groupby_model.groupby_started.connect(self.start_loading)
        self.groupby_model.groubpby_finished.connect(self.stop_loading)

    @property
    def conn(self):
        """Return sqlite connection"""
        return self._conn

    @conn.setter
    def conn(self, conn):
        """Set sqlite connection"""
        self._conn = conn
        if conn:
            self.groupby_model.set_conn(conn)

    def load(
        self,
        field_name: str,
        fields: list,
        source: str,
        filters: dict,
        order_desc: bool,
    ):
        if self.conn:
            self.groupby_model.load(field_name, fields, source, filters, order_desc)

    def stop_loading(self):
        super().stop_loading()
        self.tableview.horizontalHeader().setStretchLastSection(False)
        self.tableview.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tableview.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeToContents
        )


class GroupByViewWidget(PluginWidget):
    """Plugin to show, for any categorical field selected, the count of each unique value."""

    ENABLE = True

    REFRESH_STATE_DATA = {"fields", "filters", "source"}

    def __init__(self, parent=None, conn=None):
        super().__init__()
        self.conn = conn
        self.field_select_combo = QComboBox(self)

        self.view = GroupbyTable(conn, self)
        self.view.tableview.doubleClicked.connect(self.on_double_click)

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
        self.view.conn = conn
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
            self.field_select_combo.clear()
            self.groupby_model.clear()

    def _load_groupby(self):
        if self.conn:
            self.view.load(
                self.field_select_combo.currentText(),
                self.mainwindow.get_state_data("fields"),
                self.mainwindow.get_state_data("source"),
                self.mainwindow.get_state_data("filters"),
                self._order_desc,
            )

    def on_double_click(self):
        selected_value = (
            self.view.tableview.selectionModel()
            .currentIndex()
            .siblingAtColumn(0)
            .data(Qt.DisplayRole)
        )
        if self.mainwindow:
            filters = self.mainwindow.get_state_data("filters")

            if "$and" in filters:
                filters["$and"].append(
                    {self.view.groupby_model.get_field_name(): selected_value}
                )
            else:
                filters = {
                    "$and": [{self.view.groupby_model.get_field_name(): selected_value}]
                }
            # I know it has already been set since this dictionnary does shallow copy
            self.mainwindow: MainWindow
            print(
                "merde"
                if filters == self.mainwindow.get_state_data("filters")
                else "youpi"
            )
            self.mainwindow.set_state_data("filters", filters)
            self.mainwindow.refresh_plugins(sender=self)


if __name__ == "__main__":
    import sys
    from PySide2.QtWidgets import QApplication

    app = QApplication(sys.argv)

    conn = sql.get_sql_connection("test.db")

    w = GroupByViewWidget()
    w.conn = conn

    w.show()

    app.exec_()
