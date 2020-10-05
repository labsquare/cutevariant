from PySide2.QtCore import QRunnable, QThreadPool, QObject, Signal
from cutevariant.core.sql import get_sql_connexion
import sqlite3
from typing import Callable


class SqlRunnable(QRunnable):
    class Signals(QObject):
        started = Signal()
        finished = Signal()

    def __init__(self, conn: sqlite3.Connection, function: Callable):
        """init a runnable with connection and callable

        The callable must be a function with one conn argument as sqlite3.Connexion 

        runnable = SqlRunnable(conn, lambda conn : conn.execute("query"))

        Args:
            conn (sqlite3.Connection): sqlite3 Connexion
            function (Callable): Function with conn as argments
        """
        super().__init__()
        self.filename = conn.execute("PRAGMA database_list").fetchone()["file"]
        self.function = function
        self.results = None
        self.signals = SqlRunnable.Signals()
        self.done = False

    def run(self):
        # We are in a new thread ...
        self.done = False
        if self.function:
            self.signals.started.emit()
            self.async_conn = get_sql_connexion(self.filename)
            self.results = self.function(self.async_conn)
            self.done = True
            self.signals.finished.emit()

        else:
            self.done = True
            self.signals.finished.emit()


if __name__ == "__main__":
    from PySide2.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)

    app.exec_()
