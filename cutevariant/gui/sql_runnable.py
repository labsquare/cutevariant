# Standard imports
import sqlite3
from typing import Callable

# Qt imports
from PySide2.QtCore import QRunnable, QObject, Signal

# Custom imports
from cutevariant.core.sql import get_sql_connexion


class SqlRunnable(QObject, QRunnable):
    """Used to execute SQL/VQL queries in a separated thread

    Attributes:
        - db_file (str): File path of the database.
        - async_conn (sqlite3.Connection): sqlite3 Connection
        - function (Callable): Function to be executed
        - results: Contain the result of the threaded function.
            `None`, as long as the function has not finished its execution done.

    Signals:
        - started: Emitted when the threaded function is started.
        - finished: Emitted when the function has finished its execution.
    """
    started = Signal()
    finished = Signal()

    def __init__(self, conn: sqlite3.Connection, function: Callable):
        """Init a runnable with connection and callable

        Notes:
            Since sqlite3 Connection objects are not thread safe, we create a new
            connection based on it.

        Examples:

            >>> runnable = SqlRunnable(conn, lambda conn : conn.execute("query"))

        Args:
            conn (sqlite3.Connection): sqlite3 Connexion
            function (Callable): Function that can takes conn in its first argument.
                This function will be executed in a separated thread.
        """
        # Must instantiate the 2 constructors, especially QObject for Signals
        # Workaround for:
        # AttributeError: 'PySide2.QtCore.Signal' object has no attribute 'connect'
        QObject.__init__(self)
        QRunnable.__init__(self)
        # A valid function must be set
        assert isinstance(function, Callable)

        # Get the database filename to duplicate the connection to be thread safe
        self.db_file = conn.execute("PRAGMA database_list").fetchone()["file"]
        self.async_conn = None
        self.function = function
        self.results = None
        self.done = False

    def run(self):
        """Execute the function in a new thread

        Note:
            All the context of this function is executed into a separated thread.

        Signals:
            - started: When the threaded function is started
            - finished: When the function has finished its execution.

        Returns:
            When the job is finished, `done` is set to True.
        """
        # Create a new connection to be thread safe
        self.async_conn = get_sql_connexion(self.db_file)
        # Connection must be established
        assert self.async_conn

        self.done = False
        self.started.emit()
        self.results = self.function(self.async_conn)
        self.done = True
        self.finished.emit()


if __name__ == "__main__":
    from PySide2.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)

    app.exec_()
