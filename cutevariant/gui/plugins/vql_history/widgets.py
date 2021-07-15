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
    QAction,
    QHeaderView,
    QAbstractItemView,
    QSpacerItem,
    QStyledItemDelegate,
    QLineEdit,
)

from PySide2.QtGui import QDesktopServices, QKeySequence

# Custom imports
from cutevariant.gui import style, plugin, FIcon, MainWindow
from cutevariant.core.querybuilder import build_vql_query


from cutevariant.core import sql

from cutevariant.gui.widgets import VqlSyntaxHighlighter


from cutevariant import LOGGER

""" 
This plugin is intended to store VQL history and several information 

"""


class HistoryModel(QAbstractTableModel):

    """A model to store history.

    Each History record are composed of 5 values

    - A tag name
    - a Date
    - Time execution of VQL
    - VQL query
    - Variant count

    """

    HEADERS = ["Name", "Date", "time", "Query", "Count"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.records = []

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """ override :  Return Row Count"""
        return len(self.records)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """ override : Return Column Count """
        if parent == QModelIndex():
            return 5
        return 0

    def data(self, index: QModelIndex, role: Qt.DisplayRole):
        """ override: Return data according index and role """

        if not index.isValid():
            return None

        if role == Qt.DisplayRole:
            if index.column() == 0:
                # The tags for this query
                return self.records[index.row()][0]
            if index.column() == 1:
                # The date and time the query finished
                return self.records[index.row()][1].toString("hh:mm:ss")
            if index.column() == 2:
                # The time it took for the query
                return f"{self.records[index.row()][2]:.2f} s"
            if index.column() == 3:
                # The query itself
                return self.records[index.row()][3]
            if index.column() == 4:
                # The number of variants for this query
                return str(self.records[index.row()][4])

        if role == Qt.EditRole:
            if index.column() == 0:
                return self.records[index.row()][0]

        if role == Qt.ToolTipRole:
            return self.records[index.row()][3]

        return None

    def setData(self, index, value, role=Qt.EditRole):
        """ override : Set model data according index and role """
        if index.column() == 0:
            self.records[index.row()][0] = value
            return True
        else:
            return False

    def headerData(self, section: int, orientation: Qt.Orientation, role):
        """ override """

        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return HistoryModel.HEADERS[section]

        return None

    def add_record(
        self,
        query: str,
        count: int,
        perf_time: float,
        time: QDateTime = None,
        tags: str = None,
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
        self.records.insert(0, [tags, time, perf_time, query, count])
        self.endInsertRows()

    def from_json(self, records: dict):
        """ Load from a json serialisable object"""

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
            perf_time = record.get("perf_time", 0)
            self.records.append([tag, time, perf_time, query, count])

        self.endResetModel()

    def to_json(self) -> dict:
        """
        Return Json serialisable object
        """
        root = []
        for record in self.records:
            tags, time, perf_time, query, count = record

            # In self.records, time (first column) is a QDateTime. So we need to convert it to a string to store it
            time = str(time.toSecsSinceEpoch())
            root.append(
                {
                    "tags": tags,
                    "time": time,
                    "perf_time": perf_time,
                    "query": query,
                    "count": count,
                }
            )

        return root

    def clear(self):
        """Clear records from models"""
        self.beginResetModel()
        self.records.clear()
        self.endResetModel()

    def get_record(self, index: QModelIndex) -> list:
        """Return record corresponding to the model index

        Args:
            index (QModelIndex)

        Returns:
            list: Return record as a list of values
        """
        return self.records[index.row()]

    def sort(self, column, order=Qt.AscendingOrder):
        """
        Only sort on columns 0 (request time) and 1 (variants count returned by the request)
        """

        if column in (1, 2, 4):
            self.beginResetModel()
            self.records.sort(
                key=lambda record: record[column], reverse=(order == Qt.AscendingOrder)
            )
            self.endResetModel()
        else:
            return

    def removeRow(self, row: int):
        """Remove one row from corresponding row

        Args:
            row (int)
        """
        self.beginRemoveRows(QModelIndex(), row, row)
        del self.records[row]
        self.endRemoveRows()

    def removeRows(self, indexes: list):
        """Remove multiples records from indexes

        Args:
            indexes (list): list of QModelIndex
        """
        rows = sorted([index.row() for index in indexes], reverse=True)

        self.beginResetModel()

        for row in rows:
            print(row)

            del self.records[row]

        self.endResetModel()

    def get_query(self, index: QModelIndex) -> str:
        """Return VQL query from index

        Args:
            index (QModelIndex)

        Returns:
            str: corresponding vql query
        """
        return self.records[index.row()][3]

    def get_last_query(self) -> str:

        if self.rowCount():
            last_index = self.index(0, 0)
            return self.get_query(last_index)

        return None


class DateSortProxyModel(QSortFilterProxyModel):
    def sort(self, column, order=Qt.AscendingOrder):
        return self.sourceModel().sort(column, order)


class HistoryDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)

    def paint(self, painter, option, index):

        if index.column() == 0:

            if not index.data():
                font = QFont()
                font.setItalic(True)
                painter.setFont(font)
                painter.setPen(QPen(Qt.darkGray))
                painter.drawText(option.rect, Qt.AlignCenter, "edit ...")

        if index.column() == 3 and not option.state & QStyle.State_Selected:

            painter.save()
            painter.setClipRegion(option.rect)
            painter.setPen(QColor("red"))
            doc = QTextDocument()
            doc.setDocumentMargin(0)
            metrics = QFontMetrics(painter.font())
            area = option.rect.adjusted(5, 5, -5, -5)

            syntax = VqlSyntaxHighlighter(doc)
            vql = index.data()

            elided_vql = painter.fontMetrics().elidedText(
                vql, Qt.ElideRight, area.width()
            )
            doc.setPlainText(elided_vql)
            # highlighter_->setDocument(&doc);
            # context.palette.setColor(QPalette.Text, painter.pen().color())
            painter.translate(area.topLeft())
            doc.drawContents(painter)
            painter.restore()

        else:
            super().paint(painter, option, index)


class VqlHistoryWidget(plugin.PluginWidget):
    """Exposed class to manage VQL/SQL queries from the mainwindow"""

    LOCATION = plugin.FOOTER_LOCATION
    ENABLE = True
    REFRESH_ONLY_VISIBLE = False
    REFRESH_STATE_DATA = {"executed_query_data"}

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("VQL Editor"))

        # Create model / view
        self.view = QTableView()
        self.model = HistoryModel()
        self.delegate = HistoryDelegate()

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
        self.view.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.view.setSortingEnabled(True)
        self.view.setItemDelegate(self.delegate)

        # Hide name column (too ugly for now)
        self.view.hideColumn(0)

        self.view.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeToContents
        )
        self.view.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeToContents
        )
        self.view.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeToContents
        )

        self.view.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)

        self.view.doubleClicked.connect(self.on_double_clicked)
        #  Create toolbar
        self.toolbar = QToolBar()
        self.toolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)

        self.toolbar.addAction(
            FIcon(0xF0413), self.tr("Clear"), self.on_clear_logs_pressed
        )

        self.toolbar.addAction(
            FIcon(0xF0DAE),
            self.tr("Import..."),
            self.on_import_history_pressed,
        )

        self.toolbar.addAction(
            FIcon(0xF0DAD), self.tr("Export..."), self.on_export_history_pressed
        )

        delete_row = self.toolbar.addAction(
            FIcon(0xF04F5),
            self.tr("Remove row"),
            self.on_remove_row_pressed,
        )
        delete_row.setShortcut(QKeySequence.Delete)

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
        self.search_edit.setContentsMargins(10, 10, 10, 10)

        # Create layout
        main_layout = QVBoxLayout()
        main_layout.setSpacing(0)
        main_layout.addWidget(self.toolbar)
        main_layout.addWidget(self.view)
        main_layout.addWidget(self.search_edit)

        main_layout.setContentsMargins(0, 0, 0, 0)

        self.setLayout(main_layout)

    def on_register(self, mainwindow: MainWindow):
        """ override  """
        # mainwindow.variants_load_finished.connect(self.on_variants_load_finished)
        pass

    def on_variants_load_finished(self, count: int, elapsed_time: float):
        """Triggered when variant has been loaded from variant_view plugin and store a records if required

        Args:
            count (int)
            elapsed_time (float)
        """

        vql_query = build_vql_query(
            self.mainwindow.get_state_data("fields"),
            self.mainwindow.get_state_data("source"),
            self.mainwindow.get_state_data("filters"),
        )

        #  Do not store same query consecutively
        last_query = self.model.get_last_query()
        if vql_query != self.model.get_last_query() or last_query is None:
            self.model.add_record(vql_query, count, elapsed_time)

    def on_open_project(self, conn):
        """ override """
        self.conn = conn

    def on_refresh(self):
        """override"""
        executed_query_data = self.mainwindow.get_state_data("executed_query_data")
        if executed_query_data:
            count = executed_query_data.get("count", 0)
            elapsed_time = executed_query_data.get("elapsed_time", 0.0)
            self.on_variants_load_finished(count, elapsed_time)

    def to_json(self):
        """ override """
        return self.model.to_json()

    def from_json(self, data):
        """ override """
        self.model.from_json(data)

    def on_double_clicked(self, index: QModelIndex):
        """triggered when history record is clicked

        Args:
            index (QModelIndex): index
        """
        query = self.model.get_query(index)
        parsed_query = next(vql.parse_vql(query))
        print(parsed_query)

        self.mainwindow.set_state_data("fields", parsed_query["fields"])
        self.mainwindow.set_state_data("source", parsed_query["source"])
        self.mainwindow.set_state_data("filters", parsed_query["filters"])

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

            # Ask for a file name to load the log from
            file_name = QFileDialog.getOpenFileName(
                self,
                self.tr("Please select the file you want to load the log from"),
                QDir.home().path(),
                self.tr("Log file (*.csv *.json)"),
            )[0]

            if file_name.endswith("json"):
                with open(file_name) as file:
                    data = json.load(file)
                    self.model.from_json(data)

    def on_search_pressed(self, checked: bool):
        """Triggered when user press search button

        Args:
            checked (bool)
        """
        self.search_edit.setVisible(checked)
        self.search_edit.setFocus(Qt.MenuBarFocusReason)

    def on_clear_logs_pressed(self):
        """Clear all records with a confirm message """
        confirmation = QMessageBox.question(
            self,
            self.tr("Please confirm"),
            self.tr(
                f"Do you really want to clear whole history ?\n {len(self.model.records)} records would be definitely lost !"
            ),
        )
        if confirmation == QMessageBox.Yes:
            self.model.clear()

    def on_export_history_pressed(self):
        """
        Exports the whole history of requests for this project in a JSON file
        """

        filename = QFileDialog.getSaveFileName(
            self,
            self.tr("Please choose a file name to export your log"),
            QDir.home().path(),
            self.tr("Log file (*.json)"),
        )[0]

        if filename:

            if not filename.endswith("history.json"):
                filename += ".history.json"
            with open(filename, "w") as file:
                data = self.model.to_json()
                json.dump(data, file)

    def on_remove_row_pressed(self):
        """Remove selected records"""

        selected_indexes = self.view.selectionModel().selectedRows()
        if not selected_indexes:
            return

            confirmation = QMessageBox.question(
                self,
                self.tr("Please confirm"),
                self.tr(
                    f"Do you really want to remove this row ?\nYou cannot undo this !"
                ),
            )
            if confirmation == QMessageBox.No:
                return

        self.model.removeRows(selected_indexes)


if __name__ == "__main__":

    import sys
    import sqlite3

    app = QApplication(sys.argv)

    conn = sqlite3.connect("examples/snpeff3_test.db")

    view = VqlHistoryWidget()
    view.show()

    app.exec_()
