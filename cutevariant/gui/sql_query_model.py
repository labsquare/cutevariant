from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *
import sys

from cutevariant.gui.sql_thread import SqlThread
from cutevariant.core import sql


class AsyncQueryModel(QAbstractListModel):
    """docstring for ClassName"""

    finished = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.records = []
        self.load_thread = SqlThread()
        self.load_thread.result_ready.connect(self.on_loaded)

    @property
    def conn(self):
        return self._conn

    @conn.setter
    def conn(self, conn):
        self._conn = conn
        self.load_thread.conn = conn

    @property
    def function(self):
        return self.load_thread.function

    @function.setter
    def function(self, function):
        self.load_thread.function = function

    def rowCount(self, index=QModelIndex()):
        return len(self.records)

    def columnCount(self, index=QModelIndex()):
        return 1

    def data(self, index, role):

        if not index.isValid():
            return None

        if role == Qt.DisplayRole or role == Qt.EditRole:
            return self.records[index.row()]

        return None

    def load(self):

        if self.conn:
            self.load_thread.run()

    def on_loaded(self):

        if self.load_thread.last_error:
            print("error")
        else:
            self.beginResetModel()
            self.records = self.load_thread.results
            self.endResetModel()

        self.finished.emit()


if __name__ == "__main__":

    import sqlite3
    from cutevariant.core.importer import import_reader
    from cutevariant.core.reader import FakeReader
    import os

    class AsyncLineEdit(QLineEdit):
        """docstring for ClassName"""

        def __init__(self, parent=None):
            super().__init__(parent)
            conn = sql.get_sql_connection("/home/sacha/Dev/cutevariant/corpos3.db")
            self.model = AsyncQueryModel()
            self.model.conn = conn

            self.model.finished.connect(lambda: self.setLoading(False))

        def load(self):
            query = f"SELECT DISTINCT gene FROM annotations "
            function = lambda conn: [i["gene"] for i in conn.execute(query)]
            self.model.function = function
            self.setLoading(True)

            self._completer = QCompleter()
            self._completer.setModelSorting(QCompleter.UnsortedModel)
            self._completer.setCaseSensitivity(Qt.CaseInsensitive)
            self._completer.setModel(self.model)
            self.setCompleter(self._completer)

            self.model.load()

        def setLoading(self, active):
            if active:
                print("loading")
                self.setText("Loading")
                self.setEnabled(False)
            else:
                print("end")
                self.setText("")
                self.setEnabled(True)

        def mousePressEvent(self, event):
            self.load()

    app = QApplication(sys.argv)

    # m = AsyncQueryModel()
    # m.conn = conn

    # m.function = lambda conn: [
    #     i["gene"]
    #     for i in conn.execute("SELECT DISTINCT gene FROM annotations WHERE gene LIKE '' LIMIT 1000")
    # ]
    # m.load()
    # import time

    # ww = QWidget()
    # ll = QVBoxLayout()

    # w = QLineEdit()
    # completer = QCompleter()
    # completer.setModel(m)
    # w.setCompleter(completer)

    w = AsyncLineEdit()
    w.show()
    app.exec_()
