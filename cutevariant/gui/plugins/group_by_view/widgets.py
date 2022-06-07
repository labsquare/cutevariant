from functools import lru_cache
import sqlite3

import copy
import json

from PySide6.QtCore import (
    QAbstractTableModel,
    QItemSelection,
    QModelIndex,
    Qt,
    Signal,
    QAbstractListModel,
    QObject,
    QSize,
    QSortFilterProxyModel,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHBoxLayout,
    QInputDialog,
    QMessageBox,
    QToolBar,
    QVBoxLayout,
    QLabel,
    QWidget,
    QTabWidget,
    QTableView,
    QHeaderView,
    QSizePolicy,
    QDialog,
)
from PySide6.QtGui import (
    QIcon,
    QStandardItemModel,
    QStandardItem,
    QFont,
    QAction,
)
from cutevariant.config import Config


from cutevariant.gui.plugin import PluginWidget
from cutevariant.core import sql
from cutevariant.gui.sql_thread import SqlThread
from cutevariant.gui.widgets.groupby_widget import GroupbyTable
import cutevariant.constants as cst

from cutevariant.gui import plugin, FIcon, style, MainWindow

from cutevariant import LOGGER


class GroupByViewWidget(PluginWidget):
    """Plugin to show, for any categorical field selected, the count of each unique value."""

    ENABLE = True

    REFRESH_STATE_DATA = {"fields", "filters", "source"}

    def __init__(self, parent=None, conn=None):
        super().__init__()
        self.conn = conn
        self._order_desc = True
        self._order_by_count = True
        self._limit = 50
        self._offset = 0

        # Create QCombobox
        self.field_select_combo = QComboBox(self)
        self.field_select_combo.currentTextChanged.connect(self._load_groupby)
        self.field_select_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        # Create actions
        # self.apply_action = QAction(self)
        # self.apply_action.setIcon(FIcon(0xF0EF1))
        # self.apply_action.setText(self.tr("Create filter from selection"))
        # self.apply_action.setEnabled(False)

        # self.refresh_action = QAction(self)
        # self.refresh_action.setIcon(FIcon(0xF0450))
        # self.refresh_action.setText(self.tr("Refresh"))
        # self.refresh_action.triggered.connect(self.load)

        # Create toolbar
        self.toolbar = QToolBar(self)
        self.toolbar.setIconSize(QSize(16, 16))
        self.toolbar.addWidget(self.field_select_combo)
        # self.toolbar.addAction(self.refresh_action)
        # self.toolbar.addAction(self.apply_action)

        # Create view
        self.view = GroupbyTable(conn, self, is_checkable=False)
        self.view.tableview.doubleClicked.connect(self.on_double_click)
        self.view.tableview.setSelectionMode(QAbstractItemView.ExtendedSelection)
        # Make sure that the combobox automatically gets enabled/disabled upon loading
        self.view.groupby_model.groupby_started.connect(
            lambda: self.field_select_combo.setEnabled(False)
        )

        self.view.groupby_model.groubpby_finished.connect(self.on_loaded)

        # self.view.tableview.selectionModel().selectionChanged.connect(
        #     lambda s, d: self.apply_action.setEnabled(len(s) != 0)
        # )

        # Create layout

        self.total_label = QLabel()
        self.total_label.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        self.total_label.setAlignment(Qt.AlignCenter)
        self.total_label.setMinimumHeight(30)

        layout = QVBoxLayout(self)
        layout.addWidget(self.toolbar)
        layout.addWidget(self.total_label)
        layout.addWidget(self.view)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        self.setWindowTitle(self.tr("Group By"))
        self.setWindowIcon(FIcon(0xF1860))

    def on_open_project(self, conn: sqlite3.Connection):
        """override"""
        self.conn = conn
        self.view.conn = conn

        # Load config
        self.view.groupby_model.load_config()

        self.on_refresh()

    def on_close_project(self):
        self.view.groupby_model.clear()

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
            previous_selection = self.field_select_combo.currentText()
            current_fields = self.mainwindow.get_state_data("fields")

            # Block signals before clearing so that the currentTextChanged signal doesn't fire with empty text...
            self.field_select_combo.blockSignals(True)
            self.field_select_combo.clear()
            self.field_select_combo.addItems(current_fields)
            self.field_select_combo.blockSignals(False)
            if previous_selection in current_fields:
                # Select the same field as previously selected for user's comfort
                self.field_select_combo.setCurrentText(previous_selection)
            self._load_groupby()

        else:
            self.field_select_combo.clear()
            self.view.groupby_model.clear()

    def _load_groupby(self):
        if self.conn:
            self.view.load(
                self.field_select_combo.currentText(),
                self.mainwindow.get_state_data("fields"),
                self.mainwindow.get_state_data("source"),
                self.mainwindow.get_state_data("filters"),
            )

    def on_double_click(self):
        selected_value = (
            self.view.tableview.selectionModel()
            .currentIndex()
            .siblingAtColumn(0)
            .data(Qt.DisplayRole)
        )
        if self.mainwindow:
            self.add_condition_to_filters(
                {self.view.groupby_model.get_field_name(): selected_value}
            )

    def on_apply(self):
        selected_values = [
            idx.data(Qt.DisplayRole) for idx in self.view.tableview.selectionModel().selectedRows(0)
        ]
        if selected_values:
            self.add_condition_to_filters(
                {self.view.groupby_model.get_field_name(): {"$in": selected_values}}
            )

    def add_condition_to_filters(self, condition: dict):
        filters = copy.deepcopy(self.mainwindow.get_state_data("filters"))

        if "$and" in filters:
            for index, cond in enumerate(filters["$and"]):
                if list(cond.keys())[0] == list(condition.keys())[0]:
                    filters["$and"][index] = condition
                    break
            else:
                filters["$and"].append(condition)
        else:
            filters = {"$and": [condition]}

        self.mainwindow: MainWindow
        self.mainwindow.set_state_data("filters", filters)
        self.mainwindow.refresh_plugins(sender=self)
        self.load()

    def on_loaded(self):

        self.field_select_combo.setEnabled(True)

        # Show total
        total = self.view.groupby_model.rowCount()
        self.total_label.setText(f"<b> Total: </b> {total}")


if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)

    conn = sql.get_sql_connection("test.db")

    w = GroupByViewWidget()
    w.conn = conn

    w.show()

    app.exec_()
