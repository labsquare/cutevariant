# Qt imports
from PySide2.QtCore import QObject

# Custom imports
from .plugin import QueryPluginWidget
from cutevariant.core import Query
from cutevariant.commons import logger

LOGGER = logger()


class QueryDispatcher(QObject):
    """Redirect query between widgets

    If one of the widget emits a `changed` signal, then all belonging widgets
    change their query except the sender.
    """

    def __init__(self):
        super().__init__()
        self.widgets = []
        self._query = None

    def addWidget(self, widget: QueryPluginWidget):
        """Add a widget into the router

        :param widget: a query widget and connect its `query_changed` event to
            the slot `update_all_widgets()`.
        """
        self.widgets.append(widget)
        widget.query_changed.connect(self.update_all_widgets)

    @property
    def query(self):
        """Get current query
        :return: Return current query
        """
        return self._query

    @query.setter
    def query(self, query: Query):
        """Set query and update the query of all widgets

        :param query: a Query object
        """
        self._query = query
        for widget in self.widgets:
            widget.query = query

    def update_all_widgets(self):
        """Dispatch a `query_changed` triggered from one widget to all widgets
        except the sender and the invisible widgets.
        """
        # Call on_query_changed of all referenced widgets
        for widget in self.widgets:
            if widget != self.sender() and widget.isVisible():
                LOGGER.debug(
                    "QueryDispatcher:update_all_widgets:: change event for %s",
                    widget.__class__.__name__,
                )
                widget.on_change_query()
