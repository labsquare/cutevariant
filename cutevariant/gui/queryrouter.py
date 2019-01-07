from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *

from cutevariant.gui.abstractquerywidget import AbstractQueryWidget
from cutevariant.core import Query


class QueryRouter(QObject):
    """ 
	This class redirect query between widget. 
	If a widget emit a 'changed' signal then all belongs widgets change their query except the widget emitter. 
	"""

    def __init__(self):
        super().__init__()
        self.widgets = []
        self.query = None

    def addWidget(self, widget: AbstractQueryWidget):
        self.widgets.append(widget)
        widget.changed.connect(self.widgetChanged)

    def setQuery(self, query: Query):
        self.query = query
        for widget in self.widgets:
            widget.setQuery(self.query)

    def getQuery(self):
        return self.query

    def widgetChanged(self):
        """ this method is trigger from one widget """
        sender_widget = self.sender()

        if sender_widget is not None:
            #  update query from sender widget
            self.query = sender_widget.getQuery()

            print(self.query)
            print(self.query.sql())

            #  change query for all widget except sender
            for widget in self.widgets:
                if widget != sender_widget:
                    widget.setQuery(self.query)

                    # widget must have : setQueryBuilder, updateQueryBuilder , changed Signals
