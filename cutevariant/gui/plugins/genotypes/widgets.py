"""Plugin to Display genotypes variants 
"""
import typing

# Qt imports
from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *

# Custom imports
from cutevariant.core import sql, command
from cutevariant.core.reader import BedReader
from cutevariant.gui import plugin, FIcon, style
from cutevariant.commons import logger, DEFAULT_SELECTION_NAME


LOGGER = logger()

PHENOTYPE_STR = {0: "unaffected", 1: "affected"}


class GenotypesModel(QAbstractTableModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.items = []
        self.conn = None
        self._headers = ["gene", "phenotype"]

    def rowCount(self, parent: QModelIndex) -> int:
        return len(self.items)

    def columnCount(self, parent: QModelIndex) -> int:
        return 2

    def data(self, index: QModelIndex, role: Qt.ItemDataRole) -> typing.Any:

        if not index.isValid():
            return None

        if role == Qt.DisplayRole:
            if index.column() == 0:
                return self.items[index.row()]["sample"]

            if index.column() == 1:
                phenotype = self.items[index.row()]["phenotype"]
                return PHENOTYPE_STR.get(phenotype, 0)

        if role == Qt.DecorationRole:
            if index.column() == 0:
                gt = self.items[index.row()]["genotype"]
                icon = style.GENOTYPE.get(gt, style.GENOTYPE[-1])["icon"]
                return QIcon(FIcon(icon))

    def headerData(
        self, section: int, orientation: Qt.Orientation, role: int
    ) -> typing.Any:

        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self._headers[section]

        return None

    def load(self, variant_id):

        if self.conn:

            query = f"""SELECT samples.name as 'sample', samples.phenotype as 'phenotype',  sv.gt as 'genotype' FROM samples 
                    LEFT JOIN sample_has_variant sv ON samples.id = sv.sample_id 
                    AND sv.variant_id = {variant_id}"""

            self.beginResetModel()
            self.items.clear()
            for record in self.conn.execute(query):
                self.items.append(dict(record))

            self.endResetModel()


class GenotypesWidget(plugin.PluginWidget):
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

        self.view = QTableView()
        self.view.setShowGrid(False)
        self.model = GenotypesModel()

        self.view.setModel(self.model)

        vlayout = QVBoxLayout()
        vlayout.setContentsMargins(0, 0, 0, 0)
        vlayout.addWidget(self.view)
        self.setLayout(vlayout)

    def on_open_project(self, conn):
        self.model.conn = conn

    def on_refresh(self):
        self.current_variant = self.mainwindow.get_state_data("current_variant")
        variant_id = self.current_variant["id"]

        self.model.load(variant_id)

        self.view.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.view.setSelectionBehavior(QAbstractItemView.SelectRows)


if __name__ == "__main__":

    import sqlite3
    import sys
    from PySide2.QtWidgets import QApplication

    app = QApplication(sys.argv)

    app.exec_()
