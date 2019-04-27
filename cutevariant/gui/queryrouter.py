# Qt imports
from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *

# Custom imports
from .plugin import QueryPluginWidget
from cutevariant.core import Query
from cutevariant.commons import logger

LOGGER = logger()

class QueryRouter(QObject):
    """
    This class redirect query between widgets.
    If one of the widget emit a 'changed' signal then all belongs widgets change their query except the sender.
    """

    def __init__(self):
        super().__init__()
        self.widgets = []
        self._query = None

    def addWidget(self, widget: QueryPluginWidget):
        """
        Add a widget into the router

        :param widget: a query widget
        """
        self.widgets.append(widget)
        widget.query_changed.connect(self.on_change_query)

    @property
    def query(self):
        """
        :return: Return current query
        """
        return self._query

    @query.setter
    def query(self, query: Query):
        """
        Update query for all widgets

        :param query: a Query object
        """
        self._query = query
        for widget in self.widgets:
            widget.query = query


        #self.on_query_changed()

    def on_change_query(self):
        """
        this method is trigger from one widget
        """

        #  call on_query_changed
        for widget in self.widgets:
            if widget != self.sender():
                widget.on_change_query()
