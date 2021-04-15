from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *
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

        self.beginResetModel()
        self.entities = []
        next_url = f"{URL_PREFIX}{VERSION}/dataset"

        while next_url:
            try:
                response = urlopen(next_url)
                data = response.read().decode("utf-8")
                data = json.loads(data)
                if data["next"]:
                    next_url = f"{URL_PREFIX}{VERSION}{data['next']}"
                    self.entities += data["entities"]

            except:
                break

        self.endResetModel()


class HZGeneSetModel(QAbstractListModel):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.genesets = []
        self.page = 1

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

        self.beginResetModel()
        self.genesets = []
        next_url = f"{URL_PREFIX}{endpoint}?cursor={self.page}"

        response = urlopen(next_url)
        data = response.read().decode("utf-8")
        data = json.loads(data)
        # self.genesets += data

        for geneset in data["geneSets"]:
            # Don't know why they put a stupid suffix with the source name ... remove it
            geneset["name"] = re.sub(r"/.+$", "!", geneset["name"])
            self.genesets.append(geneset)

        self.endResetModel()


class HZGeneModel(QAbstractListModel):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.genes = []
        self.page = 1

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

        self.beginResetModel()
        self.genes = []
        next_url = f"{URL_PREFIX}{endpoint}?cursor={self.page}"

        response = urlopen(next_url)
        data = response.read().decode("utf-8")
        data = json.loads(data)
        # self.genesets += data
        # self.genes += data["genes"]
        self.genes += data["associations"]
        self.endResetModel()


class HarmonizomeWidget(QWidget):
    """docstring for ClassName"""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.combo = QComboBox()
        self.geneset_view = QListView()
        self.gene_view = QListView()

        self.dataset_model = HZDataSetModel()
        self.geneset_model = HZGeneSetModel()
        self.gene_model = HZGeneModel()

        self.combo.setModel(self.dataset_model)
        self.combo.activated.connect(self.on_dataset_changed)

        self.geneset_view.setModel(self.geneset_model)
        self.geneset_view.activated.connect(self.on_geneset_changed)
        self.gene_view.setModel(self.gene_model)

        self.dataset_model.load()

        vlayout = QVBoxLayout(self)
        vlayout.addWidget(self.combo)
        vlayout.addWidget(self.geneset_view)
        vlayout.addWidget(self.gene_view)

    def on_dataset_changed(self):

        href = self.combo.currentData()
        self.geneset_model.load(href)

    def on_geneset_changed(self, index):
        href = index.data(Qt.UserRole)
        self.gene_model.load(href)


if __name__ == "__main__":

    app = QApplication(sys.argv)

    w = HarmonizomeWidget()

    w.show()
    app.exec_()
