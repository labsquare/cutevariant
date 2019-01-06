from PySide2.QtWidgets import *
from PySide2.QtCore import *
from cutevariant.core import Query


class AbstractQueryWidget(QWidget):

    #  signals
    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

    def setQuery(self, query: Query):
        raise NotImplemented()

    def getQuery(self):
        raise NotImplemented()
