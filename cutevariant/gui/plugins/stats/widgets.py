import sqlite3

from PySide2.QtGui import *
from PySide2.QtWidgets import *
from PySide2.QtCore import *

from cutevariant.core.sql import get_sql_connection, get_field_info, get_fields



from cutevariant.gui.sql_thread import SqlThread

from cutevariant.gui import style, plugin, FIcon

from cutevariant import LOGGER


class StatsModel(QAbstractTableModel):

    stats_loaded = Signal()
    stats_is_loading = Signal(bool)

    error_raised = Signal(str)
    interrupted = Signal()
    no_stats = Signal()

    metrics = {
        "mean": "The mean value of this field",
        "std": "Standard deviation",
        "min": "Lowest value of this field",
        "max": "Highest value of this field",
        "count": "Number of annotations for this field",
        "q1": "First quartile",
        "median": "Median",
        "q3": "Third quartile",
    }

    def __init__(self):
        super().__init__()

        self.cache = {}
        self.conn = None
        self.current_table = []

        self._load_stats_thread = SqlThread(self.conn)
        self._load_stats_thread.started.connect(
            lambda: self.stats_is_loading.emit(True)
        )
        self._load_stats_thread.finished.connect(
            lambda: self.stats_is_loading.emit(False)
        )
        self._load_stats_thread.result_ready.connect(self.on_stats_loaded)
        self._load_stats_thread.error.connect(self.error_raised)

        self._user_has_interrupt = False

        self.field_name = ""

    def is_stats_loading(self):
        return self._load_stats_thread.isRunning()

    def clear(self):
        """Reset the current model

        - clear variants list
        - total of variants is set to 0
        - emit variant_loaded signal
        """
        self.beginResetModel()
        self.current_table.clear()
        self.endResetModel()
        self.stats_loaded.emit()

    @property
    def conn(self):
        """
        Returns sqlite connection
        """
        return self._conn

    @conn.setter
    def conn(self, conn):
        self._conn = conn
        if conn:
            self._load_stats_thread.conn = conn

    def columnCount(self, index=QModelIndex()):
        return 2

    def rowCount(self, index=QModelIndex()):
        return len(self.current_table)

    def on_stats_loaded(self):
        self.beginResetModel()

        self.current_table.clear()

        if self.field_name not in self.cache:
            self.cache[self.field_name] = self._load_stats_thread.results

        self.current_table = list(self._load_stats_thread.results.items())

        if self.current_table:
            self.stats_loaded.emit()
        else:
            self.no_stats.emit()

        self.endResetModel()

    def data(self, index: QModelIndex, role):

        if not self.current_table:
            return

        if role == Qt.DisplayRole:

            return str(self.current_table[index.row()][index.column()])

        if role == Qt.ToolTipRole:
            metric_name = self.current_table[index.row()][0]
            return StatsModel.metrics.get(
                metric_name,
                self.tr(
                    "Oooops, something's wrong, I have no description for this one..."
                ),
            )

    def headerData(self, section, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return ["Field name", "Field value"][section]

    def interrupt(self):
        """Interrupt current query if active

        This is a blocking function...

        call interrupt and wait for the error_raised signals ...
        If nothing happen after 1000 ms, by pass and continue
        If I don't use the dead time, it is waiting for an infinite time
        at startup ... Because at startup, loading is called 2 times.
        One time by the register_plugin and a second time by the plugin.show_event

        Shamelessly copy-pasted from VariantView ;)
        """

        interrupted = False

        if self._load_stats_thread:
            if self._load_stats_thread.isRunning():
                self._user_has_interrupt = True
                self._load_stats_thread.wait(1000)
                interrupted = True

        if interrupted:
            self.interrupted.emit()

    def load(self, field_name):
        """
        Asynchronously loads statistical data about field_name column
        """
        if not self.conn:
            return

        if self.is_stats_loading():
            LOGGER.debug(
                "Cannot load data. Thread is not finished. You can call interrupt() "
            )
            return

        self.field_name = field_name

        if field_name in self.cache:
            self._load_stats_thread.results = self.cache[field_name]
            self.on_stats_loaded()
        else:
            self._load_stats_thread.start_function(
                lambda conn: get_field_info(conn, field_name, StatsModel.metrics.keys())
            )


class LoadingTableView(QTableView):
    """Movie animation displayed on VariantView for long SQL queries executed
    in background.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_loading = False
        self.error_message = None

    def paintEvent(self, event: QPainter):

        if self.is_loading():
            painter = QPainter(self.viewport())

            painter.drawText(
                self.viewport().rect(), Qt.AlignCenter, self.tr("Loading ...")
            )

        if self.error_message:
            painter = QPainter(self.viewport())

            painter.drawText(self.viewport().rect(), Qt.AlignCenter, self.error_message)

        else:
            super().paintEvent(event)

    def set_loading(self, loading=False):
        self._is_loading = loading
        self.viewport().update()

    def on_loaded(self):
        self.error_message = None
        self.viewport().update()

    def on_error(self, msg: str):
        self.error_message = msg
        self.viewport().update()

    def is_loading(self):
        return self._is_loading


class StatsWidget(plugin.PluginWidget):
    """
    Widget to show basic stats about a column in the cutevariant database
    """

    ENABLE = False

    error_raised = Signal(str)

    def __init__(self, conn=None, parent=None):
        super().__init__(parent)
        self.setWindowIcon(FIcon(0xF0128))

        self.conn = conn
        self.combobox_field = QComboBox(self)
        self.tableview_stats = LoadingTableView(self)

        layout = QVBoxLayout(self)
        layout.addWidget(self.combobox_field)
        layout.addWidget(self.tableview_stats)

        self.stats_model = StatsModel()
        self.tableview_stats.setModel(self.stats_model)

        self.combobox_field.currentTextChanged.connect(
            self.on_current_field_selected_changed
        )

        self.stats_model.stats_is_loading.connect(self.tableview_stats.set_loading)
        self.stats_model.error_raised.connect(self.tableview_stats.on_error)
        self.stats_model.stats_loaded.connect(self.tableview_stats.on_loaded)

        self.stats_model.error_raised.connect(self.on_error)
        self.stats_model.stats_loaded.connect(self.on_stats_loaded)

    def on_current_field_selected_changed(self, new_text):
        if self.conn:
            self.stats_model.load(new_text)

    def on_stats_loaded(self):
        if self.stats_model.rowCount() != 0:
            self.tableview_stats.horizontalHeader().setSectionResizeMode(
                0, QHeaderView.ResizeToContents
            )
            self.tableview_stats.horizontalHeader().setSectionResizeMode(
                1, QHeaderView.ResizeToContents
            )

    def on_error(self, error_msg):
        LOGGER.error(error_msg)

    def set_connection(self, conn: sqlite3.Connection):
        self.conn = conn
        self.combobox_field.clear()
        self.combobox_field.addItems(
            [
                field["name"]
                for field in get_fields(self.conn)
                if field["type"] in ("float", "int")
            ]
        )
        self.stats_model.conn = conn

        self.stats_model.load(self.combobox_field.currentText())

    def on_open_project(self, conn: sqlite3.Connection):
        self.set_connection(conn)


class TestWidget(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.file_menu = self.menuBar().addMenu(self.tr("File"))
        self.file_menu.addAction(self.tr("Open"), self.open_database)
        self.file_menu.addAction(
            self.tr("Open hard-coded file name"),
            lambda: self.stats_widget.set_connection(
                get_sql_connection("/home/charles/Projets cutevariant/CFTR.db")
            ),
        )

        self.stats_widget = StatsWidget()
        self.setCentralWidget(self.stats_widget)

    def open_database(self):
        db_path = QFileDialog.getOpenFileName(
            self,
            self.tr("Please choose a cutevariant database file"),
            QDir.homePath(),
            self.tr("Cutevariant projects (*.db)"),
        )[0]
        conn = None
        if db_path:
            conn = get_sql_connection(db_path)
        if conn:
            self.stats_widget.set_connection(conn)


if __name__ == "__main__":
    import sys
    from PySide2.QtWidgets import QApplication

    app = QApplication(sys.argv)

    w = TestWidget()
    w.show()

    app.exec_()
