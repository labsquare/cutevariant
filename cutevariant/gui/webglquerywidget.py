from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWebEngineWidgets import QWebEngineView, QWebEnginePage


from cutevariant.gui.ficon import FIcon


from .plugin import QueryPluginWidget
from cutevariant.core import Query
from cutevariant.core import sql
from collections import Counter



class WebGLQueryWidget(QueryPluginWidget):
    def __init__(self, parent = None):
        super().__init__(parent)
        self.setWindowTitle("web GL")


        self.view = QWebEngineView()
        self.view.setUrl("https://www.rcsb.org/3d-view/1A3N/1")
        print(self.view.page().runJavaScript("document.getElementById('ngl-ui')"))


        layout = QVBoxLayout()
        layout.setContentsMargins(0,0,0,0)
        layout.addWidget(self.view)

        self.setLayout(layout)


    def setQuery(self, query: Query):

        self.query = query 

       



    def getQuery(self):
        return self.query  # Useless , this widget is query read only 

