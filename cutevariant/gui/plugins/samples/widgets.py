"""Plugin to Display genotypes variants 
"""
import typing
from functools import partial
import time
import copy
import re

# Qt imports
from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *


# Custom imports
from cutevariant.core import sql, command
from cutevariant.core.reader import BedReader
from cutevariant.gui import plugin, FIcon, style
from cutevariant.commons import DEFAULT_SELECTION_NAME


from cutevariant import LOGGER
from cutevariant.gui.sql_thread import SqlThread

PHENOTYPE_STR = {0: "Unknown phenotype", 1: "Unaffected", 2: "Affected"}
PHENOTYPE_COLOR = {0: "#d3d3d3", 1: "#006400", 2: "#ff0000"}
SEX_ICON = {0: 0xF0766, 1: 0xF029D, 2: 0xF029C}


class SamplesModel(QAbstractTableModel):

    samples_are_loading = Signal(bool)
    error_raised = Signal(str)
    load_started = Signal()
    load_finished = Signal()
    interrupted = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.conn = None
        self.items = []
        self._fields = []
        self._fields_descriptions = {}

        # Creates the samples loading thread
        self._load_samples_thread = SqlThread(self.conn)

        # Connect samples loading thread's signals (started, finished, error, result ready)
        self._load_samples_thread.started.connect(
            lambda: self.samples_are_loading.emit(True)
        )
        self._load_samples_thread.finished.connect(
            lambda: self.samples_are_loading.emit(False)
        )
        self._load_samples_thread.result_ready.connect(self.on_samples_loaded)
        self._load_samples_thread.error.connect(self.error_raised)

        self._user_has_interrupt = False

    def rowCount(self, parent: QModelIndex = QModelIndex) -> int:
        """override"""
        return len(self.items)

    def columnCount(self, parent: QModelIndex = QModelIndex) -> int:
        """override"""
        return len(self._fields) + 1

    def data(self, index: QModelIndex, role: Qt.ItemDataRole) -> typing.Any:
        """override"""
        if not index.isValid():
            return None

        item = self.items[index.row()]
        field = self.headerData(index.column(), Qt.Horizontal, Qt.DisplayRole)

        if role == Qt.DisplayRole:
            if index.column() == 0:
                return item["name"]

            else:
                return item.get(field, "error")

        if role == Qt.DecorationRole:
            if index.column() == 0:
                return QIcon(FIcon(SEX_ICON.get(item["sex"], 0xF02D6)))
            if field == "gt":
                icon = style.GENOTYPE.get(item[field], style.GENOTYPE[-1])["icon"]
                return QIcon(FIcon(icon))

        if role == Qt.ToolTipRole:
            if index.column() == 0:
                return f"""{item['name']} (<span style="color:{PHENOTYPE_COLOR.get(item['phenotype'],'lightgray')}";>{PHENOTYPE_STR.get(item['phenotype'],'Unknown phenotype')}</span>)"""

            else:
                description = self._fields_descriptions.get(field, "")
                return f"<b>{field}</b><br/> {description} "

        # if role == Qt.ForegroundRole and index.column() == 0:
        #     phenotype = self.items[index.row()]["phenotype"]
        #     return QColor(PHENOTYPE_COLOR.get(phenotype, "#FF00FF"))

    def headerData(
        self, section: int, orientation: Qt.Orientation, role: int
    ) -> typing.Any:

        if orientation == Qt.Horizontal and role == Qt.DisplayRole:

            if section == 0:
                return "sample"
            else:
                return self._fields[section - 1]

        return None

    def load_fields(self):
        self.beginResetModel()
        if self.conn:

            self._fields = []
            self._fields_descriptions = {}
            for field in sql.get_field_by_category(self.conn, "samples"):
                self._fields.append(field["name"])
                self._fields_descriptions[field["name"]] = field["description"]

        self.endResetModel()

    def on_samples_loaded(self):

        self.beginResetModel()
        self.items.clear()
        if self._fields:
            self.items = self._load_samples_thread.results

        self.endResetModel()

        # # Save cache
        # self._load_variant_cache[
        #     self._sample_hash
        # ] = self._load_variant_thread.results.copy()

        self._end_timer = time.perf_counter()
        self.elapsed_time = self._end_timer - self._start_timer
        self.load_finished.emit()

    def load(self, variant_id):
        """Start async queries to get sample fields for the selected variant

        Called by:
            - on_change_query() from the view.
            - sort() and setPage() by the model.

        See Also:
            :meth:`on_samples_loaded`
        """
        if self.conn is None:
            return

        if self.is_running():
            LOGGER.debug(
                "Cannot load data. Thread is not finished. You can call interrupt() "
            )
            self.interrupt()

        # Create load_func to run asynchronously: load samples
        load_samples_func = partial(
            sql.get_sample_annotations_by_variant,
            variant_id=variant_id,
            fields=self._fields,
        )

        # Start the run
        self._start_timer = time.perf_counter()

        # # Create function HASH for CACHE
        # self._sample_hash = hash(load_samples_func.func.__name__ + str(load_samples_func.keywords))

        self.load_started.emit()

        # # Launch the first thread "count" or by pass it using the cache
        # if self._sample_hash in self._load_count_cache:
        #     self._load_variant_thread.results = self._load_count_cache[self._count_hash]
        #     self.on_samples_loaded()
        # else:
        self._load_samples_thread.conn = self.conn
        self._load_samples_thread.start_function(
            lambda conn: list(load_samples_func(conn))
        )

    def sort(self, column: int, order: Qt.SortOrder) -> None:
        self.beginResetModel()
        sorting_key = (
            "phenotype"
            if column == 0
            else self.headerData(column, Qt.Horizontal, Qt.DisplayRole)
        )
        print(self.items)
        self.items = sorted(
            self.items,
            key=lambda i: i[sorting_key],
            reverse=order == Qt.DescendingOrder,
        )
        self.endResetModel()

    def interrupt(self):
        """Interrupt current query if active

        This is a blocking function...

        call interrupt and wait for the error_raised signals ...
        If nothing happen after 1000 ms, by pass and continue
        If I don't use the dead time, it is waiting for an infinite time
        at startup ... Because at startup, loading is called 2 times.
        One time by the register_plugin and a second time by the plugin.show_event
        """

        interrupted = False

        if self._load_samples_thread:
            if self._load_samples_thread.isRunning():
                self._user_has_interrupt = True
                self._load_samples_thread.interrupt()
                self._load_samples_thread.wait(1000)
                interrupted = True

        if interrupted:
            self.interrupted.emit()

    def is_running(self):
        if self._load_samples_thread:
            return self._load_samples_thread.isRunning()
        return False


class SamplesWidget(plugin.PluginWidget):
    """Widget displaying the list of avaible selections.
    User can select one of them to update Query::selection
    """

    ENABLE = True
    REFRESH_STATE_DATA = {"current_variant"}

    def __init__(self, parent=None, conn=None):
        """
        Args:
            parent (QWidget)
            conn (sqlite3.connexion): sqlite3 connexion
        """
        super().__init__(parent)

        self.toolbar = QToolBar()
        self.view = QTableView()
        self.view.setShowGrid(False)
        self.view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.view.setSortingEnabled(True)
        self.view.setIconSize(QSize(22, 22))
        self.model = SamplesModel()

        self.setWindowIcon(FIcon(0xF0A8C))

        self.view.setModel(self.model)

        vlayout = QVBoxLayout()
        vlayout.setContentsMargins(0, 0, 0, 0)
        vlayout.addWidget(self.toolbar)
        vlayout.addWidget(self.view)
        self.setLayout(vlayout)

        self.view.doubleClicked.connect(self._on_double_clicked)

        self.field_action = self.toolbar.addAction("Field")
        self.toolbar.widgetForAction(self.field_action).setPopupMode(
            QToolButton.InstantPopup
        )

    def _create_field_menu(self):

        self.menu = QMenu(self)
        self.field_action.setMenu(self.menu)

        # Obligé de faire un truc degeulasse pour avoir un

        for col in range(1, self.model.columnCount()):
            field = self.model.headerData(col, Qt.Horizontal, Qt.DisplayRole)
            action = QAction(field, self)
            self.menu.addAction(action)
            action.setCheckable(True)

            if field == "gt":
                action.setChecked(True)
                self.view.showColumn(col)
            else:
                action.setChecked(False)
                self.view.hideColumn(col)

            fct = partial(self._toggle_column, col)
            action.toggled.connect(fct)

    def _toggle_column(self, col: int, show: bool):
        """hide/show columns"""
        if show:
            self.view.showColumn(col)
        else:
            self.view.hideColumn(col)

    def _on_double_clicked(self, index: QModelIndex):

        sample_name = index.siblingAtColumn(0).data()

        if sample_name:
            filters = copy.deepcopy(self.mainwindow.get_state_data("filters"))
            key = f"samples.{sample_name}.gt"
            condition = {key: {"$gte": 1}}

            if "$and" in filters:
                for index, field in enumerate(filters["$and"]):
                    if re.match(r"samples\.\w+\.gt", list(field.keys())[0]):
                        filters["$and"][index] = condition
                        break
                else:
                    filters["$and"].append(condition)
            else:
                filters = {"$and": [condition]}

            print("FILTERS", filters)
            self.mainwindow.set_state_data("filters", filters)
            self.mainwindow.refresh_plugins(sender=self)

    def on_open_project(self, conn):
        self.model.conn = conn
        self.model.load_fields()
        self._create_field_menu()

    def on_refresh(self):
        self.current_variant = self.mainwindow.get_state_data("current_variant")
        variant_id = self.current_variant["id"]

        self.model.load(variant_id)

        self.view.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeToContents
        )
        self.view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.view.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)


if __name__ == "__main__":

    import sqlite3
    import sys
    from PySide2.QtWidgets import QApplication

    app = QApplication(sys.argv)

    conn = sqlite3.connect("/DATA/dev/cutevariant/corpos2.db")
    conn.row_factory = sqlite3.Row

    view = SamplesWidget()
    view.on_open_project(conn)
    view.show()

    app.exec_()
