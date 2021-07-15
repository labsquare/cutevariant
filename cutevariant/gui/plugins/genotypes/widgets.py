"""Plugin to Display genotypes variants 
"""
import typing
from functools import partial

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

PHENOTYPE_STR = {0: "Missing", 1: "Unaffected", 2: "Affected"}
PHENOTYPE_COLOR = {0: QColor("lightgray"), 1: QColor("green"), 2: QColor("red")}
SEX_ICON = {0: 0xF0766, 1: 0xF029D, 2: 0xF029C}


class GenotypesModel(QAbstractTableModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.items = []
        self.conn = None
        self._fields = []

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
            return f"""
            <b>Sample</b>: {item["name"]}</br>
            <b>Phenotype</b>:{item["phenotype"]}</br>
            """

        if role == Qt.ForegroundRole and index.column() == 0:
            phenotype = self.items[index.row()]["phenotype"]
            return PHENOTYPE_COLOR.get(phenotype, QColor("#FF00FF"))

    def headerData(
        self, section: int, orientation: Qt.Orientation, role: int
    ) -> typing.Any:

        if orientation == Qt.Horizontal and role == Qt.DisplayRole:

            if section == 0:
                return "sample"
            else:
                return self._fields[section - 1]

        return None

    def load(self, variant_id):

        if self.conn:
            self.beginResetModel()
            self.items.clear()
            self.items = list(
                sql.get_sample_annotations_by_variant(
                    self.conn, variant_id, self._fields
                )
            )

            self.endResetModel()

    def sort(self, column: int, order: Qt.SortOrder) -> None:
        pass
        # self.beginResetModel()
        # sorting_key = "phenotype" if column == 1 else "genotype"
        # self.items = sorted(
        #     self.items,
        #     key=lambda i: i[sorting_key],
        #     reverse=order == Qt.DescendingOrder,
        # )
        # self.endResetModel()

    def clear(self):
        self.beginResetModel()
        self.items = []
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

        self.toolbar = QToolBar()
        self.view = QTableView()
        self.view.setShowGrid(False)
        self.view.setSortingEnabled(True)
        self.view.setIconSize(QSize(22, 22))
        self.model = GenotypesModel()

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

        for col in range(1, self.model.columnCount()):
            field = self.model.headerData(col, Qt.Horizontal, Qt.DisplayRole)
            action = QAction(field, self)
            self.menu.addAction(action)
            action.setCheckable(True)
            action.setChecked(field == "gt")
            if field != "gt":
                self.view.horizontalHeader().hideSection(col)
            else:
                self.view.horizontalHeader().hideSection(col)
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
            # samples['NA12877'].gt > 1
            self.mainwindow.set_state_data(
                "filters", {"$and": [{f"samples.{sample_name}.gt": {"$gte": 1}}]}
            )
            self.mainwindow.refresh_plugins(sender=None)

    def on_open_project(self, conn):
        self.model.conn = conn
        self.model.clear()
        self.model._fields = [
            i["name"] for i in sql.get_field_by_category(conn, "samples")
        ]
        self._create_field_menu()

    def on_refresh(self):
        self.current_variant = self.mainwindow.get_state_data("current_variant")
        variant_id = self.current_variant["id"]

        self.model.load(variant_id)

        self.view.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeToContents
        )
        # self.view.setSelectionBehavior(QAbstractItemView.SelectRows)
        # self.view.horizontalHeader().setStretchLastSection(True)
        self.view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.view.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)


if __name__ == "__main__":

    import sqlite3
    import sys
    from PySide2.QtWidgets import QApplication

    app = QApplication(sys.argv)

    conn = sqlite3.connect("/DATA/dev/cutevariant/corpos2.db")
    conn.row_factory = sqlite3.Row

    view = GenotypesWidget()
    view.on_open_project(conn)
    view.show()

    app.exec_()
