from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *
from enum import Enum

from .plugin import QueryPluginWidget
from cutevariant.core import Query
from cutevariant.gui.ficon import FIcon
from cutevariant.gui.fields import *


class FilterQueryWidget(QueryPluginWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(self.tr("Filter"))
        self.view = QTreeView()
        self.model = FilterModel(None)
        self.delegate = FilterDelegate()

        self.view.setModel(self.model)
        self.view.setItemDelegate(self.delegate)

        layout = QVBoxLayout()
        layout.addWidget(self.view)
        layout.setContentsMargins(0, 0, 0, 0)

        self.setLayout(layout)

        self.model.filterChanged.connect(self.on_filter_changed)

    def on_init_query(self):
        """ Overrided """
        self.model.conn = self.query.conn
        
        #self.model.query = self.query

    def on_change_query(self):
        """ override methods """
        #self.model.load()
        print(self.query.filter)
        self.model.load(self.query.filter)
        self.view.header().setSectionResizeMode(1,QHeaderView.ResizeToContents)

    def on_filter_changed(self):
        
        self.query.filter = self.model.fromItem()
        self.query_changed.emit()




    