from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *

from .plugin import QueryPluginWidget
from cutevariant.core import Query


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
        widget.changed.connect(self.widgetChanged)

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

    def widgetChanged(self):
        """ 
        this method is trigger from one widget 
        """

        #  Get the wiget which send the signal changed
        sender_widget = self.sender()

        if sender_widget is not None:
            #  update query from sender widget
            query = sender_widget.query
            print(query)

            if not query:
                return

            self._query = query

            print(self.query.sql())

            #  change query for all widget except sender
            for widget in self.widgets:
                if widget != sender_widget:
                    widget.query = query
