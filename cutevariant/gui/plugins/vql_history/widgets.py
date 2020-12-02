# Qt imports
from PySide2.QtCore import Qt, QAbstractTableModel
from PySide2.QtWidgets import QToolBar, QVBoxLayout, QApplication

from cutevariant.gui import style, plugin, FIcon
from cutevariant.core.querybuilder import build_vql_query
from cutevariant.commons import logger

LOGGER = logger()


class HistoryModel(QAbstractTableModel):

    HEADERS = ["time", "count", "query"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.records = []

    def rowCount(self, parent: QModelIndex) -> int:
        """ override """
        return len(self.records)

    def columnCount(self, parent: QModelIndex) -> int:
        """ override """
        return 3

    def data(self, index: QModelIndex, role):
        """ override """

        if not index.isValid():
            return None

        if role == Qt.DisplayRole:
            if index.column() == 0:
                return self.records[index.row()][0].toString()
            if index.column() == 1:
                return str(self.records[index.row()][1])
            if index.column() == 2:
                return self.records[index.row()][2]
        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role):
        """ override """

        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.HEADERS[section]

        return None

    def add_record(self, query: str, count: int):
        """Add a record into the model
        
        Args:
            query (str): A VQL query
            count (int): the total count of variant returns by the VQL query
        """

        now = QDateTime().currentDateTime()

        self.beginInsertRows(QModelIndex(), 0, 0)
        self.records.append((now, count, query))
        self.endInsertRows()

    def clear_records(self):
        """Clear records from models
        """
        self.beginResetModel()
        self.records.clear()
        self.endResetModel()


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
        self.view.setModel(self.model)
        self.view.setAlternatingRowColors(True)
        self.view.horizontalHeader().setStretchLastSection(True)
        self.view.verticalHeader().hide()
        self.view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.view.setSelectionMode(QAbstractItemView.SingleSelection)

        #  Create toolbar
        self.toolbar = QToolBar()

        # Create layout
        main_layout = QVBoxLayout()
        main_layout.addWidget(self.toolbar)
        main_layout.addWidget(self.view)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.setLayout(main_layout)

    def on_register(self, mainwindow):
        pass

    def on_open_project(self, conn):
        pass

    def on_close(self):
        pass

    def on_refresh(self):

        vql_query = build_vql_query(
            self.mainwindow.state.fields,
            self.mainwindow.state.source,
            self.mainwindow.state.filters,
            self.mainwindow.state.group_by,
            self.mainwindow.state.having,
        )

        self.model.add_record(vql_query, 0)


if __name__ == "__main__":

    import sys
    import sqlite3

    app = QApplication(sys.argv)

    conn = sqlite3.connect("/home/sacha/Dev/cutevariant/examples/test.db")

    view = VqlHistoryWidget()
    view.show()

    app.exec_()
