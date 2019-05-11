# Qt imports
from PySide2.QtWidgets import QWidget
from PySide2.QtCore import Signal

# Custom imports
from cutevariant.core import Query


class PluginWidget(QWidget):
    """Handy class for common methods of QueryPluginWidget and VariantPluginWidget"""

    def __init__(self, parent=None):
        super().__init__(parent)

    def objectName(self):
        """Override: Return an object name based on windowTitle

        .. note:: Some plugins don't set objectName attribute and so their state
            can't be saved with MainWindow's saveState function.
        """
        return self.windowTitle().lower()


class QueryPluginWidget(PluginWidget):
    """Base class for all widgets which observe a Query

    .. seealso:: queryrooter.py
    """

    # Signals
    # When the query's widget changed
    query_changed = Signal()
    # When the widget emits a message to be displayed in the status bar
    message = Signal(str)

    @property
    def query(self):
        return self._query

    @query.setter
    def query(self, query: Query):
        self._query = query
        self.on_init_query()

    def on_change_query(self):
        """Called by the queryrouter each time a belong widget send a
        query_changed signal
        """
        raise NotImplementedError(self.__class__.__name__)

    def on_init_query(self):
        """Called by the queryrouter when query is set"""
        raise NotImplementedError(self.__class__.__name__)


class VariantPluginWidget(PluginWidget):
    """Base class for all widgets which get variant data when clicking on it
    from the main view
    """

    def set_variant(self, variant):
        raise NotImplementedError(self.__class__.__name__)
