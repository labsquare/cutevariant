from cutevariant.constants import GENOTYPE_DESC
import sqlite3
from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtNetwork import *
import sys
import json
import re
import os
import tempfile

from cutevariant.gui.ficon import FIcon
from cutevariant.core.sql import get_sql_connection, get_wordsets
from cutevariant.core.command import import_cmd
from cutevariant.gui.plugin import PluginDialog

import typing


URL_PREFIX = "https://maayanlab.cloud/Harmonizome"
VERSION = "/api/1.0"


class HZDataSetModel(QAbstractListModel):

    progress = Signal(int, int)
    finished = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.entities = []

        self.downloader = QNetworkAccessManager(self)
        self.current_download = None

        # Store entities that are still downloading
        self._part_entities = []

        self.title = self.tr("Databases")

    def rowCount(self, parent=QModelIndex()):
        if parent == QModelIndex():
            return len(self.entities)

        return 0

    def data(self, index, role):

        if not index.isValid():
            return None

        if role == Qt.DisplayRole or role == Qt.ToolTipRole:
            return self.entities[index.row()]["name"]

        if role == Qt.UserRole:
            return self.entities[index.row()]["href"]

        if role == Qt.DecorationRole:
            return QIcon(FIcon(0xF01BC))

        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role: int) -> typing.Any:
        if section > 0 or orientation == Qt.Vertical or role != Qt.DisplayRole:
            return

        return self.title

    def load(self):
        """Initiates model loading."""
        if self.current_download:
            self._part_entities.clear()
            self.current_download.abort()

        self.current_download = self.downloader.get(
            QNetworkRequest(f"{URL_PREFIX}{VERSION}/dataset")
        )
        self.current_download.finished.connect(self.on_batch_loaded)

    def on_batch_loaded(self):
        data = str(self.current_download.readAll(), encoding="utf-8")
        if data:
            data = json.loads(data)
            if "entities" in data:
                self.current_download.close()
                self._part_entities += data["entities"]
                if "next" in data and data["next"]:
                    self.current_download = self.downloader.get(
                        QNetworkRequest(QUrl(f"{URL_PREFIX}{data['next']}"))
                    )
                    self.current_download.finished.connect(self.on_batch_loaded)
                else:
                    self.current_download = None
                    self.on_download_finished()

    def on_download_finished(self):
        self.beginResetModel()
        self.entities = self._part_entities.copy()  # Copy to avoid surprises !
        self.finished.emit()
        self.endResetModel()


class HZGeneSetModel(QAbstractListModel):

    progress = Signal(int, int)
    finished = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.downloader = QNetworkAccessManager(self)
        self.current_download = None

        self.genesets = []

        self.database_endpoint = ""
        self.database_name = ""

    def rowCount(self, parent=QModelIndex()):
        if parent == QModelIndex():
            return len(self.genesets)

        return 0

    def data(self, index, role):

        if not index.isValid():
            return None

        if role == Qt.DisplayRole or role == Qt.ToolTipRole:
            return self.genesets[index.row()]["name"]

        if role == Qt.UserRole:
            return self.genesets[index.row()]["href"]

    def headerData(self, section: int, orientation: Qt.Orientation, role: int) -> typing.Any:
        if (
            section > 0
            or orientation == Qt.Vertical
            or (role != Qt.DisplayRole and role != Qt.ToolTipRole)
        ):
            return

        return (
            self.tr(f"Geneset from {self.database_name}")
            if self.database_name
            else self.tr("No database selected")
        )

    def load(self, endpoint: str, database_name: str):
        """Initiates model loading."""
        self.beginResetModel()
        self.genesets.clear()
        self.endResetModel()

        # If we cannot download, it can only mean one thing: we are already downloading.
        # Therefore, abort
        if self.current_download:
            self.current_download.abort()

        self.database_name = database_name
        self.database_endpoint = endpoint

        self.current_download = self.downloader.get(
            QNetworkRequest(f"{URL_PREFIX}{self.database_endpoint}")
        )
        # No need for batch downloads or cursors, the response is in one block !
        self.current_download.finished.connect(self.on_download_finished)
        self.current_download.downloadProgress.connect(
            lambda cur, tot: self.progress.emit(cur, tot)
        )

    def on_download_finished(self):
        self.finished.emit()
        if self.current_download.isReadable():
            try:
                data = str(self.current_download.readAll(), encoding="utf-8")
            except:
                try:
                    data = str(self.current_download.readAll(), encoding="ascii")
                except:
                    # Give up
                    return
            if data:
                data = json.loads(data)
                self.current_download.close()

                self.beginResetModel()
                for geneset in data["geneSets"]:
                    geneset["name"] = re.sub(r"/.+$", "", geneset["name"])
                    self.genesets.append(geneset)
                self.endResetModel()


class HZGeneModel(QAbstractListModel):

    progress = Signal(int, int)
    finished = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.downloader = QNetworkAccessManager(self)
        self.current_download = None

        self.genes = []

        self.gene_set = ""
        self.end_point = ""

    def rowCount(self, parent=QModelIndex()):
        if parent == QModelIndex():
            return len(self.genes)

        return 0

    def data(self, index, role):

        if not index.isValid():
            return None

        if role == Qt.DisplayRole:
            return self.genes[index.row()]["gene"]["symbol"]

    def headerData(self, section: int, orientation: Qt.Orientation, role: int) -> typing.Any:
        if (
            section > 0
            or orientation == Qt.Vertical
            or (role != Qt.DisplayRole and role != Qt.ToolTipRole)
        ):
            return

        return (
            self.tr(f"Genes in {self.gene_set}")
            if self.gene_set
            else self.tr("No gene set selected")
        )

    def load(self, endpoint: str, gene_set: str):
        """Initiates model loading.
        Aborts if it was downloading
        """

        # ------------------------To show to the user that we are reloading
        self.beginResetModel()
        self.genes.clear()
        self.endResetModel()
        if self.current_download:
            self.current_download.abort()

        self.end_point = endpoint
        self.gene_set = gene_set

        self.current_download = self.downloader.get(
            QNetworkRequest(f"{URL_PREFIX}{self.end_point}")
        )
        # No need for batch downloads or cursors, the response is in one block !
        self.current_download.finished.connect(self.on_download_finished)
        self.current_download.downloadProgress.connect(
            lambda cur, tot: self.progress.emit(cur, tot)
        )

    def on_download_finished(self):
        self.finished.emit()
        if self.current_download.isReadable():
            data = str(self.current_download.readAll(), encoding="utf-8")
            if data:
                data = json.loads(data)
                self.current_download.close()

                self.beginResetModel()
                self.genes = data["associations"]
                self.endResetModel()

    def clear(self):
        if self.current_download:
            # Will discard downloaded data
            self.current_download.abort()
        self.beginResetModel()
        self.genes.clear()
        self.gene_set = ""
        self.endResetModel()


class LoadingTableView(QTableView):
    def __init__(self, parent=None):
        super().__init__(parent)

        self._is_loading = False

    def paintEvent(self, event: QPainter):

        if self._is_loading:
            painter = QPainter(self.viewport())

            painter.drawText(self.viewport().rect(), Qt.AlignCenter, self.tr("Loading ..."))

        else:
            super().paintEvent(event)

    def start_loading(self):
        self._is_loading = True
        self.viewport().update()

    def stop_loading(self):
        self._is_loading = False
        self.viewport().update()


class FilteredListWidget(QWidget):
    """Convenient widget that displays a QTableView along with a search line edit.
    This class takes care of displaying a loading message when start_loading is called (and removes the message when stop_loading is called).
    """

    # Convenient signal to tell when current index changes. Returns index in **source** coordinates
    current_index_changed = Signal(QModelIndex)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.tableview = LoadingTableView(self)
        self.proxy = QSortFilterProxyModel(self)

        self.tableview.setModel(self.proxy)
        self.tableview.horizontalHeader().setStretchLastSection(True)
        self.tableview.setAlternatingRowColors(True)
        self.tableview.setSelectionMode(QAbstractItemView.ExtendedSelection)

        self.search_edit = QLineEdit(self)

        self.search_edit.textChanged.connect(self.proxy.setFilterRegExp)

        layout = QVBoxLayout(self)
        layout.addWidget(self.tableview)
        layout.addWidget(self.search_edit)

        self.tableview.verticalHeader().hide()

        self.tableview.selectionModel().currentChanged.connect(self.on_current_index_changed)

    def set_model(self, model: QAbstractItemModel):
        self.proxy.setSourceModel(model)

    def start_loading(self):
        self.search_edit.hide()
        self.tableview.start_loading()

    def stop_loading(self):
        self.tableview.stop_loading()
        self.search_edit.show()

    def on_current_index_changed(self, current: QModelIndex, previous: QModelIndex):
        # Prevents errors when filtering an empty list
        if current.isValid():
            self.current_index_changed.emit(self.proxy.mapToSource(current))


class GeneSelectionDialog(QDialog):
    def __init__(self, initial_selection: typing.List[str] = None, parent: QWidget = None):
        super().__init__(parent)

        self.view = FilteredListWidget(self)

        self.model = QStringListModel([])
        self.view.tableview.horizontalHeader().hide()
        self.view.set_model(self.model)

        self.clear_selection_btn = QPushButton(self.tr("Clear list"), self)
        self.remove_selection_item_btn = QPushButton(self.tr("Remove selected gene(s)"), self)
        self.view.tableview.setSelectionMode(QAbstractItemView.ExtendedSelection)

        self.buttons_layout = QHBoxLayout()
        self.buttons_layout.addWidget(self.clear_selection_btn)
        self.buttons_layout.addWidget(self.remove_selection_item_btn)

        self.exit_btn_box = QDialogButtonBox(self)
        self.exit_btn_box.setStandardButtons(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.exit_btn_box.rejected.connect(self.reject)
        self.exit_btn_box.accepted.connect(self.accept)

        layout = QVBoxLayout(self)

        layout.addLayout(self.buttons_layout)
        layout.addWidget(self.view)
        layout.addWidget(self.exit_btn_box)

        self.gene_selection = initial_selection

        self.clear_selection_btn.clicked.connect(self.on_clear_selectiion_clicked)
        self.remove_selection_item_btn.clicked.connect(self.on_remove_selection_items_clicked)

    def on_remove_selection_items_clicked(self):
        selected_genes = [
            index.data(Qt.DisplayRole)
            for index in self.view.tableview.selectionModel().selectedIndexes()
        ]
        self.gene_selection = list(set(self.gene_selection).difference(selected_genes))

    def on_clear_selectiion_clicked(self):
        self.gene_selection = []

    @property
    def gene_selection(self) -> typing.List[str]:
        return self._gene_selection

    @gene_selection.setter
    def gene_selection(self, value: typing.List[str]):
        self._gene_selection = value
        self.model.setStringList(self._gene_selection)


class HarmonizomeWidget(QWidget):
    """docstring for ClassName"""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.dataset_view = FilteredListWidget(self)
        self.geneset_view = FilteredListWidget(self)
        self.gene_view = FilteredListWidget(self)

        self.dataset_model = HZDataSetModel(self)
        self.geneset_model = HZGeneSetModel(self)
        self.gene_model = HZGeneModel(self)

        self.dataset_view.set_model(self.dataset_model)
        self.geneset_view.set_model(self.geneset_model)
        self.gene_view.set_model(self.gene_model)

        # A bit cheating (directly accessing tableview member) but clearly NBD
        self.dataset_view.tableview.setSelectionMode(QAbstractItemView.SingleSelection)
        self.geneset_view.tableview.setSelectionMode(QAbstractItemView.SingleSelection)

        self._init_layout()
        self._init_connections()

        self.dataset_model.load()
        self.dataset_view.start_loading()

        self.selected_dataset = ("", "")  # Stores UserRole,DisplayRole (in this order)
        self.selected_geneset = ("", "")  # Stores UserRole,DisplayRole (in this order)

        # This set keeps track of the genes selection
        self.selected_genes = set()

    def _init_connections(self):

        # When the user selects another dataset
        self.dataset_view.current_index_changed.connect(self.on_dataset_index_changed)

        # When the user selects another gene set
        self.geneset_view.current_index_changed.connect(self.on_geneset_index_changed)

        # Setup connections that tell fancy loading states to hide
        self.dataset_model.finished.connect(self.dataset_view.stop_loading)
        self.geneset_model.finished.connect(self.geneset_view.stop_loading)
        self.gene_model.finished.connect(self.gene_view.stop_loading)

    def _init_layout(self):
        layout = QHBoxLayout(self)
        layout.setMargin(0)
        layout.addWidget(self.dataset_view)
        layout.addWidget(self.geneset_view)
        layout.addWidget(self.gene_view)

    def on_dataset_index_changed(self, index: QModelIndex):
        """Called when the dataset combo gets activated"""
        # This is because activated combo doesn't mean the current index has changed...
        if index.data(Qt.DisplayRole) != self.selected_dataset[0]:
            self.selected_dataset = (
                index.data(Qt.UserRole),
                index.data(Qt.DisplayRole),
            )
            # In selected_dataset, first role is UserRole (href), second is DisplayRole

            self.geneset_model.load(*self.selected_dataset)
            self.geneset_view.start_loading()
            self.gene_model.clear()

    def on_geneset_index_changed(self, index: QModelIndex):
        """Called when the user selected another gene set

        Args:
            index (QModelIndex): Index of the selected gene set in the gene set model
        """

        # Test if the index actually changed
        if index.data(Qt.DisplayRole) != self.selected_geneset[0]:
            self.selected_geneset = (
                index.data(Qt.UserRole),
                index.data(Qt.DisplayRole),
            )
            self.gene_model.load(*self.selected_geneset)
            self.gene_view.start_loading()

    @Slot()
    def on_add_genes_to_selection_pressed(self):
        selected_genes = [
            index.data(Qt.DisplayRole)
            for index in self.gene_view.tableview.selectionModel().selectedIndexes()
        ]
        # We can only add from the view. Thus, update is the most appropriate
        self.selected_genes.update(selected_genes)

    @Slot()
    def on_selection_info_pressed(self):
        dlg = GeneSelectionDialog(self.get_selected_genes(), self)
        # We don't change selected_genes if cancel was pressed !
        if dlg.exec_() == QDialog.Accepted:
            self.selected_genes = set(dlg.gene_selection)

    def get_selected_genes(self):
        return list(self.selected_genes)


class HarmonizomeWordsetDialog(PluginDialog):

    ENABLE = True

    def __init__(self, conn: sqlite3.Connection = None, parent: QWidget = None) -> None:
        super().__init__(parent)

        self.setWindowTitle(self.tr("Create wordset from harmonizome database"))
        self.harmonizome_widget = HarmonizomeWidget(self)

        self.add_wordset_btn = QPushButton(self.tr("Create wordset"), self)
        self.cancel_btn = QPushButton(self.tr("Cancel"), self)
        self.selection_info_button = QPushButton(self.tr("My selection (0 genes)"))
        self.selection_add_button = QPushButton(self.tr("Add genes to selection"), self)

        self.label_hyperlink = QLabel(
            self.tr(
                "<b>Harmonizome</b> can be found <a href='https://maayanlab.cloud/Harmonizome/'>here</a>"
            ),
            self,
        )
        self.label_hyperlink.setOpenExternalLinks(True)

        self.cancel_btn.setDefault(True)

        self.cancel_btn.clicked.connect(self.reject)

        self.selection_add_button.clicked.connect(
            self.harmonizome_widget.on_add_genes_to_selection_pressed
        )
        self.selection_add_button.clicked.connect(self.update_selection_info_button)
        self.selection_info_button.clicked.connect(
            self.harmonizome_widget.on_selection_info_pressed
        )
        self.selection_info_button.clicked.connect(self.update_selection_info_button)
        self.add_wordset_btn.clicked.connect(self.add_wordset)

        self.buttons_layout = QHBoxLayout()
        self.buttons_layout.addWidget(self.cancel_btn)
        self.buttons_layout.addItem(QSpacerItem(30, 0, QSizePolicy.Expanding, QSizePolicy.Fixed))
        self.buttons_layout.addWidget(self.selection_add_button)
        self.buttons_layout.addWidget(self.selection_info_button)
        self.buttons_layout.addWidget(self.add_wordset_btn)

        layout = QVBoxLayout(self)
        layout.addWidget(self.label_hyperlink)
        layout.addWidget(self.harmonizome_widget)
        layout.addLayout(self.buttons_layout)

        self.set_names = []

        self.conn = conn

    @property
    def conn(self):
        return self._conn

    @conn.setter
    def conn(self, value: sqlite3.Connection):
        self._conn = value
        # We just changed conn, so the set_names are not relevant anymore
        self.set_names.clear()
        if self._conn:
            self.set_names = [data["name"] for data in get_wordsets(self._conn)]

    def import_wordset(self, words, wordset_name):
        """Import given words into a new wordset in database

        Warnings:
            There is NO CHECK on manual user's inputs! Except during DB insertion.

        Args:
            words(list): List of words to be inserted
            wordset_name(str): Name of the word set

        Note:
            Copy pasted from word_set plugin... Code replication is bad !

        Returns:
            (boolean): Status of the wordset creation
        """

        if self.conn:
            # Dump the list in a temporary file
            fd, filename = tempfile.mkstemp()
            with open(filename, "w") as file:
                [file.write(word + "\n") for word in words]

            # Import the content of the temp file in DB
            result = import_cmd(self.conn, "wordsets", wordset_name, filename)

            if not result["success"]:
                QMessageBox.critical(
                    self,
                    self.tr("Error while importing set"),
                    self.tr("Error while importing set '%s'") % wordset_name,
                )

            os.close(fd)
            os.remove(filename)
            return result["success"]

    def add_wordset(self):
        """Display a window to allow to add/edit/remove word sets

        The set is then imported in database.
        """

        wordset_name = None
        while not wordset_name:
            wordset_name, _ = QInputDialog.getText(
                self, self.tr("Create a new set"), self.tr("Name of the new set:")
            )
            if not wordset_name:
                return

            if wordset_name in self.set_names:
                # Name already used
                QMessageBox.critical(
                    self,
                    self.tr("Error while creating set"),
                    self.tr("Error while creating set '%s'; Name is already used") % wordset_name,
                )
                wordset_name = None

        # Import and close dialog
        if self.import_wordset(self.harmonizome_widget.get_selected_genes(), wordset_name):
            QMessageBox.information(
                self,
                self.tr("Success!"),
                self.tr(f"Successfully imported wordset {wordset_name}"),
            )

            self.mainwindow.set_state_data("source", wordset_name)
            self.mainwindow.refresh_plugins()
            self.accept()

    @Slot()
    def update_selection_info_button(self):
        self.selection_info_button.setText(
            self.tr(f"My selection ({len(self.harmonizome_widget.selected_genes)}) genes")
        )


if __name__ == "__main__":

    app = QApplication(sys.argv)

    w = HarmonizomeWordsetDialog(
        get_sql_connection("/home/charles/bioinfo/cutevariant_projects/example.db")
    )
    w.show()
    app.exec_()
