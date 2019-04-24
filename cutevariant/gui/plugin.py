from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *
from cutevariant.core import Query


class PluginWidget(QWidget):
    """Handy class for methods common to QueryPluginWidget and VariantPluginWidget"""

    def __init__(self, parent=None):
        super().__init__(parent)

    def objectName(self):
        """Overrided: Return an object name based on windowTitle

        .. note:: Some plugins don't set objectName attribute and so their state
            can't be saved with MainWindow's saveState function.
        """
        return self.windowTitle().lower()


class QueryPluginWidget(PluginWidget):
    """
    This is a base class for all widget which observe a Query

    .. seealso:: queryrooter.py
    """

    # Signals
    # When the widget is modified
    query_changed = Signal()
    # When the widget emits a message to be displayed in the status bar
    message = Signal(str)

    @property
    def query(self):
        return self._query

    @query.setter
    def query(self, query: Query):
        self._query = query

    def on_query_changed(self):
        raise NotImplemented()


    def dispatch(self):
        """ Notify other widget that query has been changed """ 

        self.query_changed.emit()




class VariantPluginWidget(PluginWidget):
    """
    This is a base class for all widget which get variant data
    when clicking on it from the main view
    """

    def set_variant(self, variant):
        raise NotImplemented()
