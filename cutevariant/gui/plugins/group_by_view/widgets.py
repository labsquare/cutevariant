from functools import lru_cache
import sqlite3

import copy
import json

from PySide2.QtCore import (
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
from PySide2.QtWidgets import (
    QAbstractItemView,
    QAction,
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
)
from PySide2.QtGui import QIcon, QStandardItemModel, QStandardItem, QFont

from cutevariant.gui.plugin import PluginWidget
from cutevariant.core import sql
from cutevariant.gui.sql_thread import SqlThread
from cutevariant.gui.widgets import LoadingTableView
import cutevariant.commons as cm

from cutevariant.gui import plugin, FIcon, style, MainWindow

from cutevariant import LOGGER


class FilterProxyModel(QSortFilterProxyModel):
    """This class has only one purpose: calling the same sort method as its source model."""

    def sort(self, column: int, order: Qt.SortOrder) -> None:
        if self.sourceModel():
            self.sourceModel().sort(column, order)


class GroupbyModel(QAbstractTableModel):

    groupby_started = Signal()
    groubpby_finished = Signal()
    groupby_error = Signal()

    GENOTYPE_ICONS = {key: FIcon(val) for key, val in cm.GENOTYPE_ICONS.items()}

    def __init__(self, parent: QObject = None, conn: sqlite3.Connection = None) -> None:
        super().__init__(parent)
        self._raw_data = []
        self._conn = conn
        self.load_groupby_thread = SqlThread(self._conn)
        self.load_groupby_thread.started.connect(self.groupby_started)
        self.load_groupby_thread.finished.connect(self.groubpby_finished)
        self.load_groupby_thread.result_ready.connect(self._on_data_available)
        self.load_groupby_thread.error.connect(self._on_error)

        self._field_name = "chr"

        self._fields = ["chr", "pos", "ref", "alt"]
        self._source = "variants"
        self._filters = {}
        self._order_by_count = True

        self.is_loading = False

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """override"""
        return len(self._raw_data)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """override"""
        if parent == QModelIndex():
            return 2
        return 0

    def headerData(self, section: int, orientation: Qt.Orientation, role: int):
        """override"""
        if section not in (0, 1):
            return

        if orientation != Qt.Horizontal:
            return

        if role == Qt.DisplayRole:
            return ["Value", "Count"][section]

    def data(self, index: QModelIndex, role: int):
        """override"""

        if not self._raw_data:
            # Shouldn't be called by anyone, since in such case rowCount will be 0...
            return

        if not index.isValid():
            return

        if index.column() not in (0, 1):
            return

        if index.row() < 0 or index.row() >= self.rowCount():
            return

        if self._field_name.split(".")[-1] == "gt":
            if role == Qt.DecorationRole and index.column() == 0:
                return QIcon(
                    self.__class__.GENOTYPE_ICONS.get(
                        self._raw_data[index.row()][self._field_name],
                        self.__class__.GENOTYPE_ICONS[-1],
                    )
                )

        if role == Qt.DisplayRole:
            if self._field_name not in self._raw_data[0]:
                return (
                    self.tr(f"Invalid data. Loaded: {self._raw_data[0]['field']}")
                    if index.column() == 0
                    else self.tr(f"Current field name: {self._field_name}")
                )
            if index.column() == 0:
                return self._raw_data[index.row()][self._field_name]
            if index.column() == 1:
                return self._raw_data[index.row()]["count"]

        if role == Qt.FontRole:
            if index.column() == 0:
                font = QFont()
                font.setBold(True)
                return font

        if role == Qt.ForegroundRole:
            if index.column() == 1:
                return qApp.style().standardPalette().color(QPalette.Shadow)

        if role == Qt.TextAlignmentRole:

            if index.column() == 0:
                return Qt.AlignmentFlag(Qt.AlignLeft | Qt.AlignVCenter)

            if index.column() == 1:
                return Qt.AlignmentFlag(Qt.AlignRight | Qt.AlignVCenter)

    def clear(self):
        self._set_raw_data([])

    def set_conn(self, conn: sqlite3.Connection):
        self._conn = conn
        self.load_groupby_thread.conn = self._conn

    def sort(self, column: int, order: Qt.SortOrder):
        """Overrided: Sort data by specified column

        column (int): column id
        order (Qt.SortOrder): Qt.AscendingOrder or Qt.DescendingOrder

        """
        if column < self.columnCount():
            self._order_by_count = column == 1
            self._order_desc = order == Qt.DescendingOrder
            self.load(self._field_name, self._fields, self._source, self._filters)

    def load(
        self,
        field_name,
        fields,
        source,
        filters,
    ):
        """Counts unique values inside field_name

        Args:
            conn (sqlite3.Connection): Access to cutevariant's project database
            field_name (str): The field you want the number of unique values of
        """
        if self.is_loading:
            return
        if not self._conn:
            return

        self._field_name = field_name
        self._fields = fields
        self._source = source
        self._filters = filters
        groupby_func = lambda conn: sql.get_variant_as_group(
            conn,
            self._field_name,
            self._fields,
            self._source,
            self._filters,
            self._order_by_count,
            self._order_desc,
        )
        self.load_groupby_thread.start_function(lambda conn: list(groupby_func(conn)))
        self.is_loading = True

    def _on_data_available(self):
        self._set_raw_data(self.load_groupby_thread.results)
        self.is_loading = False

    def _on_error(self):
        QMessageBox.critical(
            None,
            self.tr("Error!"),
            self.tr(
                f"Group by thread returned error {self.load_groupby_thread.last_error}"
            ),
        )
        self.clear()
        self.groupby_error.emit()
        self.is_loading = False

    def _set_raw_data(self, raw_data: list):
        self.beginResetModel()
        self._raw_data = raw_data
        self.endResetModel()

    def get_field_name(self):
        return self._field_name


class GroupbyTable(QWidget):
    def __init__(self, conn=None, parent=None):
        super().__init__(parent=parent)
        self.conn = conn
        self.groupby_model = GroupbyModel(self)
        self.proxy = FilterProxyModel(self)
        self.tableview = LoadingTableView(self)
        self.tableview.setModel(self.proxy)
        self.tableview.setShowGrid(False)
        self.setBackgroundRole(QPalette.Base)
        self.tableview.verticalHeader().hide()
        self.tableview.horizontalHeader().hide()
        self.proxy.setSourceModel(self.groupby_model)
        self.tableview.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tableview.setSelectionBehavior(QAbstractItemView.SelectRows)

        self.groupby_model.groupby_started.connect(self.start_loading)
        self.groupby_model.groubpby_finished.connect(self.stop_loading)

        self.tableview.sortByColumn(1, Qt.DescendingOrder)
        self.tableview.setSortingEnabled(True)

        layout = QVBoxLayout(self)
        layout.addWidget(self.tableview)
        layout.setContentsMargins(0, 0, 0, 0)

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
    ):
        if self.conn:
            self.groupby_model.load(
                field_name,
                fields,
                source,
                filters,
            )

    def start_loading(self):
        self.tableview.start_loading()

    def stop_loading(self):
        self.tableview.stop_loading()
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
        self.setWindowIcon(FIcon(0xF126F))

        self.toolbar = QToolBar(self)
        self.toolbar.setIconSize(QSize(16, 16))

        # HIDE wordset button
        # self.add_selection_to_wordset_act = self.toolbar.addAction(
        #     FIcon(0xF0415), self.tr("Add selection to wordset")
        # )
        # self.add_selection_to_wordset_act.triggered.connect(
        #     self.add_selection_to_wordset
        # )

        self.view.tableview.setSelectionMode(QAbstractItemView.ExtendedSelection)

        # Add apply button
        self.apply_action: QAction = self.toolbar.addAction(
            FIcon(0xF0EF1), self.tr("Create filter from selection")
        )

        self.refresh_action: QAction = self.toolbar.addAction(
            FIcon(0xF0450), self.tr("Rerfresh")
        )
        self.refresh_action.triggered.connect(self.load)
        self.toolbar.addWidget(self.field_select_combo)

        # spacer = QWidget()
        # spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        # self.toolbar.addWidget(spacer)

        layout = QVBoxLayout(self)
        layout.addWidget(self.toolbar)
        layout.addWidget(self.view)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        self.field_select_combo.currentTextChanged.connect(self._load_groupby)

        # Make sure that the combobox automatically gets enabled/disabled upon loading
        self.view.groupby_model.groupby_started.connect(
            lambda: self.field_select_combo.setEnabled(False)
        )

        self.apply_action.setEnabled(False)

        self.view.groupby_model.groubpby_finished.connect(
            lambda: self.field_select_combo.setEnabled(True)
        )

        self.view.tableview.selectionModel().selectionChanged.connect(
            lambda s, d: self.apply_action.setEnabled(len(s) != 0)
        )

        self._order_desc = True
        self._order_by_count = True
        self._limit = 50
        self._offset = 0

    def on_open_project(self, conn: sqlite3.Connection):
        """override"""
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
            idx.data(Qt.DisplayRole)
            for idx in self.view.tableview.selectionModel().selectedRows(0)
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


if __name__ == "__main__":
    import sys
    from PySide2.QtWidgets import QApplication

    app = QApplication(sys.argv)

    conn = sql.get_sql_connection("test.db")

    w = GroupByViewWidget()
    w.conn = conn

    w.show()

    app.exec_()
