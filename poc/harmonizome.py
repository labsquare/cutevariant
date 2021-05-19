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
            self.current_download.abort()

        self.current_download = self.downloader.get(
            QNetworkRequest(f"{URL_PREFIX}{VERSION}/dataset")
        )
        self.current_download.finished.connect(self.on_batch_loaded)

    def on_batch_loaded(self):
        data = str(self.current_download.readAll(), encoding="utf-8")
        data = json.loads(data)
        self.current_download.close()
        if "next" in data and data["next"]:
            self._part_entities += data["entities"]
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

        self.dataset_model = HZDataSetModel(self)
        self.geneset_model = HZGeneSetModel(self)
        self.gene_model = HZGeneModel(self)

        self.geneset_proxymodel = QSortFilterProxyModel(self)
        self.geneset_proxymodel.setSourceModel(self.geneset_model)

        self.gene_proxymodel = QSortFilterProxyModel(self)
        self.gene_proxymodel.setSourceModel(self.gene_model)

        self.combo.setModel(self.dataset_model)
        self.combo.setEditable(True)
        self.combo.completer().setModel(self.dataset_model)
        # Below is the missing line (found at 1:59 AM)
        self.combo.completer().setCompletionRole(Qt.DisplayRole)
        self.combo.completer().setCompletionMode(QCompleter.InlineCompletion)
        self.combo.activated.connect(self.on_dataset_changed)

        self.geneset_view.setModel(self.geneset_proxymodel)
        self.geneset_view.activated.connect(self.on_geneset_changed)
        self.gene_view.setModel(self.gene_proxymodel)

        self.geneset_filter_le = QLineEdit(self)
        self.gene_filter_le = QLineEdit(self)

        self.geneset_filter_le.textChanged.connect(
            self.geneset_proxymodel.setFilterRegExp
        )

        self.geneset_progressbar = QProgressBar(self)
        self.genes_progressbar = QProgressBar(self)

        # Layout for the geneset view (also holds the combobox)
        self.db_and_geneset = QVBoxLayout()
        self.db_and_geneset.addWidget(self.combo)
        self.db_and_geneset.addWidget(self.geneset_view)
        self.db_and_geneset.addWidget(self.geneset_progressbar)
        self.db_and_geneset.addWidget(self.geneset_filter_le)

        # Layout for the gene view and its progressbar
        self.gene_view_layout = QVBoxLayout()
        self.gene_view_layout.addWidget(self.gene_view)
        self.gene_view_layout.addWidget(self.genes_progressbar)
        self.gene_view_layout.addWidget(self.gene_filter_le)

        glayout = QGridLayout(self)

        glayout.addLayout(self.db_and_geneset, 0, 0)
        glayout.addLayout(self.gene_view_layout, 0, 1)

        self.geneset_progressbar.hide()
        self.genes_progressbar.hide()

        self.dataset_model.load()

    def on_dataset_changed(self):
        """Called when the user chooses another dataset"""
        # A bit weird, but because of the autocompletion this was the only way...
        self.combo.setCurrentText(self.combo.currentData(Qt.DisplayRole))

        self.geneset_progressbar.show()
        self.geneset_model.progress.connect(self.on_geneset_progress_changed)
        self.geneset_model.finished.connect(lambda: self.geneset_progressbar.hide())

        href = self.combo.currentData(Qt.UserRole)
        self.geneset_model.load(href)

    def on_geneset_changed(self, index: QModelIndex):
        """Called when the user selected another gene set

        Args:
            index (QMOdelIndex): Index of the selected gene set in the gene set model
        """

        self.genes_progressbar.show()
        self.gene_model.progress.connect(self.on_gene_progress_changed)
        self.gene_model.finished.connect(lambda: self.genes_progressbar.hide())

        href = index.data(Qt.UserRole)
        self.gene_model.load(href)

    def on_geneset_progress_changed(self, cur: int, tot: int):
        self.geneset_progressbar.setMaximum(tot)
        self.geneset_progressbar.setValue(cur)

    def on_gene_progress_changed(self, cur: int, tot: int):
        self.genes_progressbar.setMaximum(tot)
        self.genes_progressbar.setValue(cur)


if __name__ == "__main__":

    app = QApplication(sys.argv)

    w = HarmonizomeWidget()

    w.show()
    app.exec_()
