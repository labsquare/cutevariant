import sqlite3
from cutevariant.gui import plugin, style
from cutevariant.gui import MainWindow

from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtWidgets import *

from cutevariant.core import sql

from cutevariant.gui import FIcon


class SampleModel(QAbstractTableModel):

    NAME_COLUMN = 0
    PHENOTYPE_COLUMN = 1
    SEX_COLUMN = 2
    COMMENT_COLUMN = 3

    def __init__(self, conn: sqlite3.Connection = None) -> None:
        super().__init__()
        self._samples = []
        self.conn = conn

    def clear(self):
        self.beginResetModel()
        self._samples.clear()
        self.endResetModel()

    def load(self):
        """Loads all the samples from the database"""
        if self.conn:
            self.beginResetModel()
            self._samples = list(sql.get_samples(self.conn))
            self.endResetModel()

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole):
        # Titles
        if orientation == Qt.Horizontal and role == Qt.DisplayRole and section == 0:
            return self.tr("Samples")
        if orientation == Qt.Vertical and role == Qt.DecorationRole:
            return QColor("red")

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        col = index.column()
        if role == Qt.DisplayRole and col == SampleModel.NAME_COLUMN:
            sample = self._samples[index.row()]
            return sample.get("name")
        if role == Qt.DecorationRole:
            sample = self._samples[index.row()]
            color = QApplication.palette().color(QPalette.Text)
            color_alpha = color
            color_alpha.setAlpha(50)
            if col == SampleModel.SEX_COLUMN:
                sex = sample.get("sex", None)
                if sex == 1:
                    return QIcon(FIcon(0xF029D))
                if sex == 2:
                    return QIcon(FIcon(0xF029C))
                if sex == 0:
                    return QIcon(FIcon(0xF029C, color_alpha))
            if col == SampleModel.PHENOTYPE_COLUMN:
                phenotype = sample.get("phenotype")
                if phenotype == 2:
                    return QIcon(FIcon(0xF0E95))
            if col == SampleModel.COMMENT_COLUMN:
                if sample["comment"]:
                    return QIcon(FIcon(0xF017A, color))
                else:
                    return QIcon(FIcon(0xF017A, color_alpha))

    def get_sample(self, index: QModelIndex):
        if index.row() >= 0 and index.row() < len(self._samples):
            return self._samples[index.row()]

    def rowCount(self, index: QModelIndex = QModelIndex()):
        if index == QModelIndex():
            return len(self._samples)
        else:
            return 0

    def columnCount(self, index: QModelIndex = QModelIndex()):
        if index == QModelIndex():
            return 4
        else:
            return 0


class SamplesWidget(plugin.PluginWidget):

    # Location of the plugin in the mainwindow
    # Can be : DOCK_LOCATION, CENTRAL_LOCATION, FOOTER_LOCATION
    LOCATION = plugin.DOCK_LOCATION
    # Make the plugin enable. Otherwise, it will be not loaded
    ENABLE = True

    # Refresh the plugin only if the following state variable changed.
    # Can be : fields, filters, source

    REFRESH_STATE_DATA = {"fields", "filters"}

    def __init__(self, parent=None):
        super().__init__(parent)

        self.tool_bar = QToolBar()
        self.view = QTableView()
        self.search_bar = QLineEdit()

        self.model = SampleModel(self.conn)
        self.view.setModel(self.model)
        self.setContentsMargins(0, 0, 0, 0)

        self._setup_actions()

        self.view.setContextMenuPolicy(Qt.ActionsContextMenu)
        self.view.horizontalHeader().hide()
        self.view.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.view.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.view.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.view.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.view.setShowGrid(False)
        self.view.setSelectionMode(QAbstractItemView.SingleSelection)
        self.view.setSelectionBehavior(QAbstractItemView.SelectRows)

        main_layout = QVBoxLayout(self)

        main_layout.addWidget(self.tool_bar)
        main_layout.addWidget(self.search_bar)
        main_layout.addWidget(self.view)

    def _setup_actions(self):

        self.action_next = self.tool_bar.addAction("Next")
        self.action_prev = self.tool_bar.addAction("Prev")

        self.view.addActions([self.action_next, self.action_prev])

    def on_register(self, mainwindow: MainWindow):
        """This method is called when the plugin is registered from the mainwindow.

        This is called one time at the application startup.

        Args:
            mainwindow (MainWindow): cutevariant Mainwindow
        """
        self.mainwindow = mainwindow

    def on_open_project(self, conn: sqlite3.Connection):
        """This method is called when a project is opened

                Do your initialization here.
        You may want to store the conn variable to use it later.

        Args:
            conn (sqlite3.connection): A connection to the sqlite project
        """
        self.model.clear()
        self.model.conn = conn
        self.model.load()

    def on_refresh(self):
        """This method is called from mainwindow.refresh_plugins()

        You may want to overload this method to update the plugin state
        when query changed
        """
        pass
