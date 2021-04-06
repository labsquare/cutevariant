# Standard imports
import typing
import glob
import json
import os

# Qt imports
from PySide2.QtCore import (
    Qt,
    QAbstractTableModel,
    QDateTime,
    QSettings,
    QDir,
    QUrl,
    QModelIndex,
    QSortFilterProxyModel,
)
from PySide2.QtWidgets import (
    QToolBar,
    QVBoxLayout,
    QApplication,
    QFileDialog,
    QMessageBox,
    QTableView,
    QHeaderView,
)

from PySide2.QtGui import QDesktopServices

# Custom imports
from cutevariant.gui import style, plugin, FIcon, MainWindow
from cutevariant.core.querybuilder import build_vql_query
from cutevariant.commons import logger

from cutevariant.core import sql


LOGGER = logger()


class HistoryModel(QAbstractTableModel):

    HEADERS = ["time", "count", "query", "tags"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.records = []

    def rowCount(self, parent: QModelIndex) -> int:
        """ override """
        return len(self.records)

    def columnCount(self, parent: QModelIndex) -> int:
        """ override """
        return 4

    def data(self, index: QModelIndex, role):
        """ override """

        if not index.isValid():
            return None

        if role == Qt.DisplayRole:
            if index.column() == 0:
                # The date and time for the query
                return self.records[index.row()][0].toString("dd/MM/yyyy - hh:mm:ss")
            if index.column() == 1:
                # The number of variants for this query
                return str(self.records[index.row()][1])
            if index.column() == 2:
                # The query itself
                return self.records[index.row()][2]
            if index.column() == 3:
                # The tags for this query
                return self.records[index.row()][3]

        if role == Qt.EditRole:
            if index.column() == 3:
                return self.records[index.row()][3]

        if role == Qt.ToolTipRole:
            return self.records[index.row()][3]

        return None

    def setData(self, index, value, role=Qt.EditRole):
        if index.column() == 3:
            self.records[index.row()][3] = value
            return True
        else:
            return False

    def flags(self, index):
        base_flags = super().flags(index)
        if index.column() == 3:
            return base_flags | Qt.ItemIsEditable
        else:
            return base_flags

    def headerData(self, section: int, orientation: Qt.Orientation, role):
        """ override """

        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return HistoryModel.HEADERS[section]

        return None

    def add_record(
        self, query: str, count: int, time: QDateTime = None, tags: str = None
    ):
        """Add a record into the model

        Args:
            query (str): A VQL query
            count (int): the total count of variant returns by the VQL query
            time (QDateTime): the date and time of the query, leave it to None if you want it set automatically
            tags (str): the tags associated with this query
        """

        if not time:
            time = QDateTime.currentDateTime()

        if not tags:
            tags = ""

        self.beginInsertRows(QModelIndex(), 0, 0)
        self.records.insert(0, [time, count, query, tags])
        self.endInsertRows()

    def load_from_json(self, file_name):
        with open(file_name) as device:
            records = json.load(device)

            self.beginResetModel()
            self.records.clear()

            # records is a python array from a JSON one. Each record in it has the four keys of the four columns of our model
            for record in records:
                # Get the time of query from this record (defaults to current time)
                time = record.get("time", QDateTime().currentDateTime())
                if isinstance(time, str):
                    if time.isnumeric():
                        time = QDateTime.fromSecsSinceEpoch(int(time))
                count = record.get("count", 0)
                query = record.get("query", "")
                tag = record.get("tags", "")
                self.records.append([time, count, query, tag])

            self.endResetModel()

    def save_to_json(self, file_name):
        root = []
        for record in self.records:
            time, count, query, tags = record

            # In self.records, time (first column) is a QDateTime. So we need to convert it to a string to store it
            time = str(time.toSecsSinceEpoch())
            root.append({"time": time, "count": count, "query": query, "tags": tags})

        with open(file_name, "w+") as device:
            json.dump(root, device)

    def clear_records(self):
        """Clear records from models"""
        self.beginResetModel()
        self.records.clear()
        self.endResetModel()

    def get_record(self, index: QModelIndex):
        """ Return record corresponding to the model index """
        return self.records[index.row()]

    def sort(self, column, order=Qt.AscendingOrder):
        """
        Only sort on columns 0 (request time) and 1 (variants count returned by the request)
        """

        if column <= 1:
            self.beginResetModel()
            self.records.sort(
                key=lambda record: record[column], reverse=(order == Qt.AscendingOrder)
            )
            self.endResetModel()
        else:
            return

    def get_query(self, index: QModelIndex):
        return self.records[index.row()][2]


class DateSortProxyModel(QSortFilterProxyModel):
    def sort(self, column, order=Qt.AscendingOrder):
        return self.sourceModel().sort(column, order)


class VqlHistoryWidget(plugin.PluginWidget):
    """Exposed class to manage VQL/SQL queries from the mainwindow"""

    LOCATION = plugin.FOOTER_LOCATION
    ENABLE = True
    REFRESH_ONLY_VISIBLE = False

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("VQL Editor"))

        # Create model / view
        self.view = QTableView()
        self.model = HistoryModel()

        # Setup search feature on a proxy model
        self.proxy_model = DateSortProxyModel()
        self.proxy_model.setSourceModel(self.model)

        # Search is case insensitive
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseInsensitive)

        self.proxy_model.setFilterKeyColumn(-1)

        self.view.setModel(self.proxy_model)
        self.view.setAlternatingRowColors(True)
        self.view.verticalHeader().hide()
        self.view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.view.setSelectionMode(QAbstractItemView.SingleSelection)
        self.view.setSortingEnabled(True)

        self.view.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.view.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeToContents
        )

        self.project_dir = ""

        self.view.doubleClicked.connect(self.on_double_clicked)
        #  Create toolbar
        self.toolbar = QToolBar()
        self.toolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)

        self.toolbar.addAction(
            FIcon(0xF0413), self.tr("Clear"), self.model.clear_records
        )

        load_history_from_file = self.toolbar.addAction(
            FIcon(0xF0DAE),
            self.tr("Import log"),
            self.on_import_history_pressed,
        )

        self.toolbar.addAction(
            FIcon(0xF0DAD), self.tr("Export log"), self.on_export_history_pressed
        )

        # Add search feature widget
        self.search_edit = QLineEdit()
        self.setFocusPolicy(Qt.ClickFocus)
        self.search_act = QAction(FIcon(0xF0969), self.tr("Search query..."))
        self.search_act.setCheckable(True)
        self.search_act.toggled.connect(self.on_search_pressed)
        self.search_act.setShortcutContext(Qt.WidgetShortcut)
        self.search_act.setShortcut(QKeySequence.Find)
        self.toolbar.addAction(self.search_act)
        self.view.addAction(self.search_act)

        self.search_edit.setVisible(False)
        self.search_edit.setPlaceholderText(self.tr("Search query... "))

        self.search_edit.textChanged.connect(self.proxy_model.setFilterRegExp)

        # Create layout
        main_layout = QVBoxLayout()
        main_layout.setSpacing(0)
        main_layout.addWidget(self.toolbar)
        main_layout.addWidget(self.search_edit)
        main_layout.addWidget(self.view)

        main_layout.setContentsMargins(0, 0, 0, 0)

        self.setLayout(main_layout)

    def on_register(self, mainwindow: MainWindow):
        mainwindow.variants_count_loaded.connect(self.on_variants_count_loaded)

    def on_variants_count_loaded(self, count: int):
        vql_query = build_vql_query(
            self.mainwindow.state.fields,
            self.mainwindow.state.source,
            self.mainwindow.state.filters,
            self.mainwindow.state.group_by,
            self.mainwindow.state.having,
        )

        self.model.add_record(vql_query, count)

    def on_open_project(self, conn):
        """ override """
        self.conn = conn
        self.project_full_path = sql.get_database_file_name(conn)

        # Get the project absolute directory
        self.project_dir = os.path.dirname(self.project_full_path)

        # Get the project name without the extension
        self.project_name = os.path.basename(self.project_full_path).split(".")[0]

        # Look for logs in the project directory, with name starting with log and containing the project name
        history_logs = glob.glob(f"{self.project_dir}/log*{self.project_name}*.json")
        for log in history_logs:
            try:
                self.model.load_from_json(log)
            except Exception as e:
                LOGGER.debug(
                    "An error occured while loading VQL queries history \n%s", e
                )

    def on_close(self):
        """ override """
        log_file_name = os.path.join(self.project_dir, f"log_{self.project_name}.json")
        self.model.save_to_json(log_file_name)

        super().on_close()

    def on_refresh(self):
        """"""
        pass

    def on_double_clicked(self, index: QModelIndex):
        """triggered when history record is clicked

        Args:
            index (QModelIndex): index
        """
        query = self.model.get_query(index)
        parsed_query = next(vql.parse_vql(query))
        print(parsed_query)

        self.mainwindow.state.fields = parsed_query["fields"]
        self.mainwindow.state.source = parsed_query["source"]
        self.mainwindow.state.filters = parsed_query["filters"]
        self.mainwindow.state.group_by = parsed_query["group_by"]
        self.mainwindow.state.having = parsed_query["having"]

        self.mainwindow.refresh_plugins(sender=self)

    def on_import_history_pressed(self):
        """
        Called whenever you'd like the user to load a log file into the query history.
        This feature can be useful if you'd like to share your queries with other users
        """
        confirmation = QMessageBox.question(
            self,
            self.tr("Please confirm"),
            self.tr(
                f"Do you really want to replace whole history with a new log file ?\n {len(self.model.records)} records would be definitely lost !"
            ),
        )
        if confirmation == QMessageBox.Yes:
            settings = QSettings()

            # When asking for a log file to load, try to remember where it was last time
            log_dir = settings.value(
                f"{self.project_full_path}/latest_log_dir", QDir.homePath()
            )

            # Ask for a file name to load the log from
            file_name = QFileDialog.getOpenFileName(
                self,
                self.tr("Please select the file you want to load the log from"),
                log_dir,
                self.tr("Log file (*.csv *.json)"),
            )[0]

            # Load the file into the model, according to the extension
            if file_name.endswith("csv"):
                self.model.load_from_csv(file_name)
            if file_name.endswith("json"):
                self.model.load_from_json(file_name)

            # Remember where we just loaded from last time
            settings.setValue(
                f"{self.project_full_path}/latest_log_dir",
                os.path.dirname(file_name),
            )

    def on_search_pressed(self, checked: bool):
        self.search_edit.setVisible(checked)
        self.search_edit.setFocus(Qt.MenuBarFocusReason)

    def on_clear_logs_pressed(self):
        confirmation = QMessageBox.question(
            self,
            self.tr("Please confirm"),
            self.tr(
                f"Do you really want to clear whole history ?\n {len(self.model.records)} records would be definitely lost !"
            ),
        )
        if confirmation == QMessageBox.Yes:
            self.model.clear_records()

    def on_export_history_pressed(self):
        """
        Exports the whole history of requests for this project in a JSON file
        """
        confirmation = QMessageBox.question(self, self.tr("Please conf"), text)
        settings = QSettings()
        export_log_dir = settings.value(
            f"{self.project_full_path}/export_log_dir", QDir.homePath()
        )

        filename = QFileDialog.getSaveFileName(
            self,
            self.tr("Please choose a file name to export your log"),
            export_log_dir,
            self.tr("Log file (*.json)"),
        )[0]

        settings.setValue(
            f"{self.project_full_path}/export_log_dir", os.path.dirname(filename)
        )

        self.model.save_to_json(filename)


if __name__ == "__main__":

    import sys
    import sqlite3

    app = QApplication(sys.argv)

    conn = sqlite3.connect("examples/snpeff3_test.db")

    view = VqlHistoryWidget()
    view.show()

    app.exec_()
