import typing
from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtWidgets import *

import sqlite3

from cutevariant.gui.ficon import FIcon
import cutevariant.constants as cst
from cutevariant.gui.sql_thread import SqlThread
from cutevariant.core import sql

from cutevariant.config import Config

import cutevariant.gui.widgets as widgets


class FilterProxyModel(QSortFilterProxyModel):
    """This class has only one purpose: calling the same sort method as its source model."""

    def sort(self, column: int, order: Qt.SortOrder) -> None:
        if self.sourceModel():
            self.sourceModel().sort(column, order)


class GroupbyModel(QAbstractTableModel):

    groupby_started = Signal()
    groubpby_finished = Signal()
    groupby_error = Signal()

    GENOTYPE_ICONS = {key: FIcon(val) for key, val in cst.GENOTYPE_ICONS.items()}

    def __init__(
        self, parent: QObject = None, conn: sqlite3.Connection = None, is_checkable=True
    ) -> None:
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

        # Load by config from on_openproject
        self.config_classifications = []
        self.config_sample_classifications = []

        self.is_checkable = is_checkable

    def load_config(self):
        config = Config("classifications")
        self.config_class_map = {i["number"]: i["name"] for i in config.get("variants", [])}
        self.config_sample_class_map = {i["number"]: i["name"] for i in config.get("samples", [])}

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
                return self.display_name(index.row())
            if index.column() == 1:
                return self._raw_data[index.row()]["count"]

        if role == Qt.FontRole:
            if index.column() == 0:
                font = QFont()
                font.setBold(True)
                return font

        if role == Qt.ForegroundRole:
            if index.column() == 1:
                return QApplication.instance().style().standardPalette().color(QPalette.Shadow)

        if role == Qt.TextAlignmentRole:

            if index.column() == 0:
                return int(Qt.AlignmentFlag(Qt.AlignLeft | Qt.AlignVCenter))

            if index.column() == 1:
                return int(Qt.AlignmentFlag(Qt.AlignRight | Qt.AlignVCenter))

        if role == Qt.CheckStateRole and index.column() == 0 and self.is_checkable:
            return int(Qt.Checked if self._raw_data[index.row()]["checked"] else Qt.Unchecked)

    def clear(self):
        self._set_raw_data([])

    def display_name(self, row: int):
        """Return display key name"""
        value = self._raw_data[row][self._field_name]
        if self._field_name == "classification":
            return self.config_class_map.get(value, "Unknown")

        if self._field_name.startswith("samples.") and self._field_name.endswith(".classification"):
            return self.config_sample_class_map.get(value, "Unknown")

        else:
            return value

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

    def setData(
        self, index: QModelIndex, value: typing.Any, role: int = int(Qt.DisplayRole)
    ) -> bool:
        if role == Qt.CheckStateRole and index.column() == 0 and self.is_checkable:
            self._raw_data[index.row()]["checked"] = bool(value)
            return True
        else:
            return False

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
            self.tr(f"Group by thread returned error {self.load_groupby_thread.last_error}"),
        )
        self.clear()
        self.groupby_error.emit()
        self.is_loading = False

    def _set_raw_data(self, raw_data: list):
        self.beginResetModel()
        for field_val in raw_data:
            field_val["checked"] = False
        self._raw_data = raw_data

        self.endResetModel()

    def get_field_name(self):
        return self._field_name

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        if self.is_checkable:
            return super().flags(index) | Qt.ItemIsUserCheckable
        else:
            return super().flags(index)

    def get_selected_values(self):
        return [d[self._field_name] for d in self._raw_data if d["checked"]]


class GroupbyTable(QWidget):
    def __init__(self, conn=None, parent=None, is_checkable=True):
        super().__init__(parent=parent)
        self.groupby_model = GroupbyModel(self, is_checkable=is_checkable)
        self.proxy = FilterProxyModel(self)
        self.tableview = widgets.LoadingTableView(self)
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

        self.conn = conn

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
        self.tableview.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)


class GroupbyDialog(QDialog):
    """Utility class to display the GroupbyTable"""

    def __init__(self, conn: sqlite3.Connection = None, parent: QWidget = None):
        super().__init__(parent)

        self.view = GroupbyTable(conn, self)
        self.view.tableview.setSelectionMode(QAbstractItemView.ExtendedSelection)

        self.filter_btn = QPushButton(self.tr("Filter selected values"))

        self.filter_btn.clicked.connect(self.accept)

        self.bottom_layout = QHBoxLayout()
        self.bottom_layout.addWidget(self.filter_btn)

        self.conn = conn

        self.vlayout = QVBoxLayout(self)

        # self.btn_box = QDialogButtonBox(QDialogButtonBox.Close)

        # self.btn_box.rejected.connect(self.reject)

        self.vlayout.addWidget(self.view)
        self.vlayout.addLayout(self.bottom_layout)
        # self.vlayout.addWidget(self.btn_box)

    def load(self, field, fields, source, filters):
        if self.conn:
            self.view.load(field, fields, source, filters)

    def get_selected_values(self) -> typing.List[str]:
        return self.view.groupby_model.get_selected_values()
