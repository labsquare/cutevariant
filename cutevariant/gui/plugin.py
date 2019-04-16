from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import * 
from cutevariant.core import Query


class QueryPluginWidget(QWidget):
    """
    This is a base class for all widget which observe a Query

    .. seealso:: queryrooter.py
    """

    #  signals
    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

    @property
    def query(self):
        raise NotImplemented()

    @query.setter
    def query(self, query: Query):
        raise NotImplemented()


class VariantPluginWidget(QWidget):
    """
    This is a base class for all widget which get variant data 
    when clicking on it from the main view
    """
    def __init__(self):
        super().__init__()

    def set_variant(self, variant):
        raise NotImplemented()

