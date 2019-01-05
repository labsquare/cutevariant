from PySide2.QtCore import *
from PySide2.QtWidgets import *
import sqlite3
import json

from cutevariant.gui.viewquerywidget import ViewQueryWidget
from cutevariant.gui.columnquerywidget import ColumnQueryWidget
from cutevariant.gui.filterquerywidget import FilterQueryWidget
from cutevariant.gui.queryrouter import QueryRouter

from cutevariant.core.importer import import_file
from cutevariant.core import Query


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__()
        self.toolbar = self.addToolBar("test")
        self.conn   = None
        self.view_widget   = ViewQueryWidget()
        self.column_widget = ColumnQueryWidget()
        self.filter_widget = FilterQueryWidget()
        
        # Init router 
        self.router = QueryRouter()
        self.router.addWidget(self.view_widget)
        self.router.addWidget(self.column_widget)
        self.router.addWidget(self.filter_widget)

        # Init panel 
        self.addPanel(self.column_widget)
        self.addPanel(self.filter_widget)
        self.setCentralWidget(self.view_widget)


        self.open("/tmp/qt_cutevariant.db")

    def open(self, filename):

        import_file("exemples/test.csv", filename)
        self.conn = sqlite3.connect(filename)

        query = Query(self.conn)
        query.filter = json.loads('''{"AND" : [{"field":"pos", "operator":">", "value":"322424"} ]}''')


        self.router.setQuery(query)
        


    def addPanel(self, widget, area = Qt.LeftDockWidgetArea):
        dock = QDockWidget()
        dock.setWindowTitle(widget.windowTitle())
        dock.setWidget(widget)
        self.addDockWidget(area, dock)




