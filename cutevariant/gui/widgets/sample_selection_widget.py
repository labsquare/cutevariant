from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

from cutevariant.core import sql


class SamplesModel(QAbstractTableModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._data = []
        self._headers = ["name", "family", "Statut", "Tags"]
        self.conn = None

    def rowCount(self, parent=QModelIndex()):
        return len(self._data)

    def columnCount(self, parent=QModelIndex()):
        return len(self._headers)

    def data(self, index, role):
        if not index.isValid():
            return

        if role == Qt.DisplayRole:
            sample = self._data[index.row()]
            if index.column() == 0:
                return sample["name"]

            if index.column() == 1:
                return sample["family_id"]

            if index.column() == 2:
                return sample["valid"]

            if index.column() == 3:
                return sample["tags"]

        return None

    def headerData(self, section, orientation, role):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:

            return self._headers[section]

    def load(self):
        if self.conn:
            self.beginResetModel()
            self._data = list(sql.get_samples(self.conn))
            self.endResetModel()


class SampleSelectionWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__()

        v_layout = QVBoxLayout(self)
        self.tab_widget = QTabWidget()

        v_layout.addWidget(self.tab_widget)


# @property
# def conn(self):
#     return self.samples_model.conn

# @conn.setter
# def conn(self, conn):
#     self.samples_model.conn = conn
#     self.samples_model.load()

if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)

    conn = sql.get_sql_connection("/home/sacha/test.db")

    w = SampleSelectionWidget()
    w.conn = conn
    w.show()

    app.exec()
