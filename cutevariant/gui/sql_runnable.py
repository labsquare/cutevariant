# Standard imports
import sqlite3
from typing import Callable

# Qt imports
from PySide2.QtCore import QRunnable, QObject, Signal, QThread

# Custom imports
from cutevariant.core.sql import get_sql_connection
from cutevariant.commons import logger

LOGGER = logger()


class SqlRunnable(QObject, QRunnable):
    """Used to execute SQL/VQL queries in a separated thread

    Attributes:
        - db_file (str): File path of the database.
        - async_conn (sqlite3.Connection): sqlite3 Connection
        - function (Callable): Function to be executed
        - query_number (int): (default: 0) Used to identify the finished query
            in a pool via the finished signal (see section Signals below).
        - results: Contain the result of the threaded function.
            `None`, as long as the function has not finished its execution done.

    Class attributes:
        - sql_connections_pool (dict): Mapping of thread ids as keys and
            sqlite3 Connections as values. It allows to reuse sql connections
            accros calls of run() method and benefit from their cache methods.

    Signals:
        - started: Emitted when the threaded function is started.
        - finished(int): Emitted when the function has finished its execution.
            The emitted argument is the unique ID of the executed query.
        - error(str): Emitted when the function has encountered an error during
            its execution. The message is formatted with the type and the
            message of the exception.

    Notes:
        AutoDelete flag of such objects is set to False.
        This means that QThreadPool **will not** delete these objects after
        calling run() method.
    """
    started = Signal()
    finished = Signal(int)
    error = Signal(str)

    sql_connections_pool = {}

    def __init__(self, conn: sqlite3.Connection, function: Callable = None, query_number: int = 0):
        """Init a runnable with connection and callable

        Notes:
            Since sqlite3 Connection objects are not thread safe, we create a new
            connection based on it.

        Examples:

            >>> runnable = SqlRunnable(conn, lambda conn : conn.execute("query"))
            >>> def my_func(conn):
            ...     return conn.execute("query")
            >>> runnable = SqlRunnable(conn, my_func)

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

        self._function = None
        if function:
            self.function = function

        # Get the database filename to duplicate the connection to be thread safe
        self.db_file = conn.execute("PRAGMA database_list").fetchone()["file"]
        self.async_conn = None

        self.results = None
        self.query_number = query_number
        self.setAutoDelete(False)

    def run(self):
        """Execute the function in a new thread

        Note:
            All the context of this function is executed into a separated thread.

        Signals:
            - started: When the threaded function is started
            - finished: When the function has finished its execution.
        """
        # Copy the current query number so it is attached to this run only
        query_number = int(self.query_number)

        # Use a new connection to be thread safe
        thread_id = QThread.currentThread()
        if thread_id not in self.sql_connections_pool:
            # Current thread hasn't its connection => create a new one
            # LOGGER.debug("NEW CONN for %s", thread_id)
            self.async_conn = get_sql_connection(self.db_file)
            self.sql_connections_pool[thread_id] = self.async_conn
        else:
            # Reuse sql connection
            # LOGGER.debug("REUSE CONN for %s", thread_id)
            self.async_conn = self.sql_connections_pool[thread_id]

        # Connection must be established
        assert self.async_conn

        self.started.emit()
        try:
            self.results = self.function(self.async_conn)
        except Exception as e:
            LOGGER.exception(e)
            self.error.emit("%s: %s" % (e.__class__.__name__, str(e)))
            return

        self.finished.emit(query_number)

    @property
    def function(self):
        return self._function

    @function.setter
    def function(self, value: Callable):
        # A valid function must be set
        assert isinstance(value, Callable)
        self._function = value


if __name__ == "__main__":
    from PySide2.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)

    app.exec_()
