from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtNetwork import *
import sys
from urllib.request import urlopen
import json
import re

URL_PREFIX = "https://maayanlab.cloud/Harmonizome"
VERSION = "/api/1.0"


class HZDataSetModel(QAbstractListModel):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.entities = []

        self.downloader = QNetworkAccessManager(self)
        self.current_download = None

        # Store entities that are still downloading
        self._part_entities = []

    def rowCount(self, parent=QModelIndex()):
        if parent == QModelIndex():
            return len(self.entities)

        return 0

    def data(self, index, role):

        if not index.isValid():
            return None

        if role == Qt.DisplayRole:
            return self.entities[index.row()]["name"]

        if role == Qt.UserRole:
            return self.entities[index.row()]["href"]

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
        self.endResetModel()


class HZGeneSetModel(QAbstractListModel):

    progress = Signal(int, int)
    finished = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.downloader = QNetworkAccessManager(self)
        self.current_download = None

        self.genesets = []

    def rowCount(self, parent=QModelIndex()):
        if parent == QModelIndex():
            return len(self.genesets)

        return 0

    def data(self, index, role):

        if not index.isValid():
            return None

        if role == Qt.DisplayRole:
            return self.genesets[index.row()]["name"]

        if role == Qt.UserRole:
            return self.genesets[index.row()]["href"]

    def load(self, endpoint):
        """Initiates model loading."""
        self.beginResetModel()
        self.genesets.clear()
        self.endResetModel()

        # If we cannot download, it can only mean one thing: we are already downloading.
        # Therefore, abort
        if self.current_download:
            self.current_download.abort()

        self.current_download = self.downloader.get(
            QNetworkRequest(f"{URL_PREFIX}{endpoint}")
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

    def load(self, endpoint):
        """Initiates model loading.
        Aborts if it was downloading
        """

        # ------------------------To show to the user that we are reloading
        self.beginResetModel()
        self.genes.clear()
        self.endResetModel()
        if self.current_download:
            self.current_download.abort()

        self.current_download = self.downloader.get(
            QNetworkRequest(f"{URL_PREFIX}{endpoint}")
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


# class LoadingListView(QWidget):
#     """Display a progress bar on the list view while loading"""

#     def __init__(self, parent=None):
#         super().__init__(parent)
#         self.progress_bar = QProgressBar(self)
#         self.list_view = QListView(self)

#         hboxlayout = QHBoxLayout()
#         self.setLayout(hboxlayout)

#         # Two widgets in the same layout, but you won't see them both at the same time !
#         self.layout().addWidget(self.progress_bar)
#         self.layout().addWidget(self.list_view)

#         self.progress_bar.setVisible(False)
#         self._is_loading = False

#     def start_loading(self):
#         self._is_loading = True
#         self.progress_bar.setVisible(True)
#         self.list_view.setVisible(False)
#         print("START LOADING")

#     def stop_loading(self):
#         self._is_loading = False
#         self.layout().removeWidget(self.progress_bar)
#         print("STOPPED LOADING")

#     @Slot(int, int)
#     def set_progress(self, cur: int, tot: int):
#         self.progress_bar.setMaximum(tot)
#         self.progress_bar.setValue(cur)
#         print("SET PRORGESS", cur, tot)


class HarmonizomeWidget(QWidget):
    """docstring for ClassName"""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.combo = QComboBox()
        self.geneset_view = QListView()
        self.gene_view = QListView()
        self.selection_view = QListView(self)

        self.dataset_model = HZDataSetModel(self)
        self.geneset_model = HZGeneSetModel(self)
        self.gene_model = HZGeneModel(self)

        self.geneset_proxymodel = QSortFilterProxyModel(self)
        self.geneset_proxymodel.setSourceModel(self.geneset_model)

        self.gene_proxymodel = QSortFilterProxyModel(self)
        self.gene_proxymodel.setSourceModel(self.gene_model)

        self.init_combo()
        self.init_geneset_view()
        self.init_geneview()
        self.init_selection_view()

        self.geneset_progressbar = QProgressBar(self)
        self.genes_progressbar = QProgressBar(self)

        self.geneset_progressbar.hide()
        self.genes_progressbar.hide()

        self.dataset_model.load()

        self.init_layouts()

        self.init_connections()

        self.selected_dataset = ("", "")  # Store both DisplayRole AND UserRole (href)
        self.selected_geneset = ("", "")  # Store both DisplayRole AND UserRole (href)
        self.selected_genes = set()

    def init_combo(self):
        self.combo.setModel(self.dataset_model)
        self.combo.setEditable(True)
        self.combo.completer().setModel(self.dataset_model)
        # Below is the missing line (found at 1:59 AM)
        self.combo.completer().setCompletionRole(Qt.DisplayRole)
        self.combo.completer().setCompletionMode(QCompleter.InlineCompletion)
        self.combo.setInsertPolicy(QComboBox.NoInsert)
        self.combo.activated.connect(self.on_dataset_combo_activated)

    def init_geneset_view(self):
        self.geneset_view.setModel(self.geneset_proxymodel)
        self.geneset_view.activated.connect(self.on_geneset_activated)

        self.geneset_filter_le = QLineEdit(self)
        self.geneset_filter_le.setPlaceholderText(self.tr("Search geneset..."))

        self.geneset_filter_le.textChanged.connect(
            self.geneset_proxymodel.setFilterRegExp
        )

    def init_geneview(self):
        self.gene_view.setModel(self.gene_proxymodel)

        self.gene_filter_le = QLineEdit(self)
        self.gene_filter_le.setPlaceholderText(self.tr("Search gene..."))

        self.button_add_selected_genes = QPushButton(
            self.tr("Add selected genes"), self
        )
        self.button_add_selected_genes.clicked.connect(
            self.on_add_selected_genes_pressed
        )

        self.gene_filter_le.textChanged.connect(self.gene_proxymodel.setFilterRegExp)

        self.gene_view.setSelectionMode(QAbstractItemView.ExtendedSelection)

    def init_selection_view(self):
        self.selected_genes_model = QStringListModel([], self)
        self.selection_view.setModel(self.selected_genes_model)
        self.selection_view.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.selection_view_remove_act = QAction(self.tr("Remove"), self)
        self.selection_view_remove_act.setShortcut(QKeySequence.Delete)
        self.selection_view.setAlternatingRowColors(True)

        # Does not work for some reason... Have to use a QPushButton
        self.selection_view.setContextMenuPolicy(Qt.ActionsContextMenu)
        self.selection_view_remove_act.triggered.connect(
            self.on_remove_selected_genes_triggered
        )

        self.selection_view_remove_button = QPushButton(
            self.tr("Remove selected gene"), self
        )
        self.selection_view_remove_button.clicked.connect(
            self.on_remove_selected_genes_triggered
        )

    def init_connections(self):
        # Connect geneset model signals (basically this means updating progress bar)
        self.geneset_model.progress.connect(self.on_geneset_progress_changed)
        self.geneset_model.finished.connect(lambda: self.geneset_progressbar.hide())

        # Connect genes model signals (basically this means updating progress bar)
        self.gene_model.progress.connect(self.on_gene_progress_changed)
        self.gene_model.finished.connect(lambda: self.genes_progressbar.hide())

    def init_layouts(self):
        # Layout for the geneset view (also holds the combobox)
        self.db_and_geneset = QVBoxLayout()
        # self.db_and_geneset.addWidget(QLabel(self.tr("Selected database:"), self))
        self.db_and_geneset.addWidget(self.combo)

        # self.db_and_geneset.addWidget(
        #     QLabel(self.tr("Genesets in selected database:"), self)
        # )
        self.db_and_geneset.addWidget(self.geneset_view)

        self.db_and_geneset.addWidget(self.geneset_progressbar)
        self.db_and_geneset.addWidget(self.geneset_filter_le)

        # Layout for the gene view and its progressbar
        self.gene_view_layout = QVBoxLayout()
        # self.gene_view_layout.addWidget(
        #     QLabel(self.tr("Genes in selected geneset:"), self)
        # )
        selection_button_layout = QHBoxLayout()
        selection_button_layout.addWidget(self.button_add_selected_genes)

        self.gene_view_layout.addLayout(selection_button_layout)
        self.gene_view_layout.addWidget(self.gene_view)
        self.gene_view_layout.addWidget(self.genes_progressbar)
        self.gene_view_layout.addWidget(self.gene_filter_le)

        self.selected_genes_layout = QVBoxLayout()
        self.selected_genes_layout.addWidget(self.selection_view_remove_button)
        self.selected_genes_layout.addWidget(QLabel(self.tr("Selected genes:"), self))
        self.selected_genes_layout.addWidget(self.selection_view)

        hlayout = QHBoxLayout(self)

        hlayout.addLayout(self.db_and_geneset)
        hlayout.addLayout(self.gene_view_layout)
        hlayout.addLayout(self.selected_genes_layout)

    def on_dataset_combo_activated(self):
        """Called when the dataset combo gets activated"""

        # A bit weird, but because of the autocompletion this was the only way...
        self.combo.setCurrentText(self.combo.currentData(Qt.DisplayRole))

        # It has been activated, this is the only way I found to avoid double activating
        self.focusNextChild()

        # This is because activated combo doesn't mean the current index has changed...
        if self.combo.currentData(Qt.DisplayRole) != self.selected_dataset[0]:
            self.selected_dataset = (
                self.combo.currentData(Qt.DisplayRole),
                self.combo.currentData(Qt.UserRole),
            )
            self.geneset_progressbar.show()

            href = self.combo.currentData(Qt.UserRole)
            self.geneset_model.load(href)

    def on_geneset_activated(self, index: QModelIndex):
        """Called when the user selected another gene set

        Args:
            index (QModelIndex): Index of the selected gene set in the gene set model
        """

        # Test if the index actually changed
        if (
            self.geneset_proxymodel.data(index, Qt.DisplayRole)
            != self.selected_geneset[0]
        ):
            self.selected_geneset = (
                self.geneset_proxymodel.data(index, Qt.DisplayRole),
                self.geneset_proxymodel.data(index, Qt.UserRole),
            )
            self.genes_progressbar.show()

            href = index.data(Qt.UserRole)
            self.gene_model.load(href)

    def on_geneset_progress_changed(self, cur: int, tot: int):
        self.geneset_progressbar.setMaximum(tot)
        self.geneset_progressbar.setValue(cur)

    def on_gene_progress_changed(self, cur: int, tot: int):
        self.genes_progressbar.setMaximum(tot)
        self.genes_progressbar.setValue(cur)

    def on_add_selected_genes_pressed(self):
        selected_genes = [
            index.data(Qt.DisplayRole)
            for index in self.gene_view.selectionModel().selectedIndexes()
        ]
        self.selected_genes = self.selected_genes.union(selected_genes)
        self.selected_genes_model.setStringList(self.selected_genes)

    def on_remove_selected_genes_triggered(self):
        selected_genes = [
            index.data(Qt.DisplayRole)
            for index in self.selection_view.selectionModel().selectedIndexes()
        ]
        self.selected_genes = self.selected_genes.difference(selected_genes)
        self.selected_genes_model.setStringList(self.selected_genes)


class HarmonizomeDialog(QDialog):
    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)
        self.harmonizome_widget = HarmonizomeWidget(self)
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self
        )
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

        layout = QGridLayout(self)
        layout.addWidget(self.harmonizome_widget, 0, 0)
        layout.addWidget(self.buttons, 1, 0)


if __name__ == "__main__":

    app = QApplication(sys.argv)

    w = HarmonizomeDialog()
    w.show()
    app.exec_()
