# Standard imports
import sqlite3
from typing import Callable

# Qt imports
from PySide2.QtCore import QThread, QObject, Signal

# Custom imports
from cutevariant.core.sql import get_sql_connection
from cutevariant.commons import logger

LOGGER = logger()


class SqlThread(QThread):
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
        - error(str): Emitted when the function has encountered an error during
            its execution. The message is formatted with the type and the
            message of the exception.

    Notes:
        AutoDelete flag of such objects is set to False.
        This means that QThreadPool **will not** delete these objects after
        calling run() method.
    """

    error = Signal(str)
    result_ready = Signal()

    def __init__(self, conn: sqlite3.Connection, function: Callable = None):
        """Init a Thread with sqlite connection and callable

        Notes:
            Since sqlite3 Connection objects are not thread safe, we create a new
            connection based on it.

        Examples:

            >>> thread = SqlThread(conn,lambda conn: conn.execute("query"))
            >>> thread.start()

        Args:
            conn (sqlite3.Connection): sqlite3 Connexion

        """

        super().__init__()

        self.conn = conn
        self._async_conn = None
        self.results = None
        self.function = function
        self.last_error = None
        self.hash = None
        self.cache = {}

    @property
    def conn(self) -> sqlite3.Connection:
        """Return the Application thread connection
        
        Returns:
            sqlite3.Connection
        """
        return self._conn

    @property
    def async_conn(self) -> sqlite3.Connection:
        """Return the thread connection 
        It is a clone of application connection for thread safe
        
        Returns:
            TYPE: Description
        """
        return self._async_conn

    @conn.setter
    def conn(self, conn):
        self._conn = conn
        self._async_conn = None
        self.db_file = conn.execute("PRAGMA database_list").fetchone()["file"]
        self.cache = {}


    def run(self):
        """Execute the function in a new thread

        Note:
            All the context of this function is executed into a separated thread.

        """
        self.last_error = None

        if self.function is None:
            LOGGER.exception("no function defined")
            return

        self._async_conn = get_sql_connection(self.db_file)
        assert self.async_conn

        try:
            LOGGER.debug("thread start ")

            if self.hash in self.cache and self.hash is not None:
                self.results = self.cache[self.hash]
            else:
                self.results = self.function(self.async_conn)
                self.cache[self.hash] = self.results

            LOGGER.debug("Thread finished")
        except Exception as e:
            # LOGGER.exception(e)
            self.last_error = "%s: %s" % (e.__class__.__name__, str(e))
            self.error.emit(self.last_error)
        else:
            self.result_ready.emit()

        return

    def start_function(self, function: Callable):
        """Execute a function in the thread
        
        Args:
            function (Callable): Function must take con as arguments 

        Examples:
            >>> thread.exec_function(lambda conn: conn.execute("SELECT ..."))

        """
        assert isinstance(function, Callable)
        self.function = function

        self.start()

    def interrupt(self):
        """Interrupt the thread connection

        Use this method instead of terminate.
        """
        if self.async_conn:
            self.async_conn.interrupt()

    @property
    def function(self):
        return self._function

    @function.setter
    def function(self, value: Callable):
        # A valid function must be set
        self._function = value


if __name__ == "__main__":
    from PySide2.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)

    app.exec_()
