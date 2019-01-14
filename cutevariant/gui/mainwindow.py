from PySide2.QtCore import *
from PySide2.QtWidgets import *
import sqlite3
import json
import os

from cutevariant.gui.viewquerywidget import ViewQueryWidget
from cutevariant.gui.columnquerywidget import ColumnQueryWidget
from cutevariant.gui.filterquerywidget import FilterQueryWidget
from cutevariant.gui.selectionquerywidget import SelectionQueryWidget

from cutevariant.gui.queryrouter import QueryRouter

from cutevariant.core.importer import import_file
from cutevariant.core import Query


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__()
        self.toolbar = self.addToolBar("test")
        self.conn = None
        self.view_widgets = []
        self.column_widget = ColumnQueryWidget()
        self.filter_widget = FilterQueryWidget()
        self.selection_widget = SelectionQueryWidget()
        self.tab_view = QTabWidget()

        # Init router
        self.router = QueryRouter()
        # self.router.addWidget(self.view_widget)
        self.router.addWidget(self.column_widget)
        self.router.addWidget(self.filter_widget)
        self.router.addWidget(self.selection_widget)

        #  Init panel
        self.addPanel(self.column_widget)
        self.addPanel(self.filter_widget)
        self.addPanel(self.selection_widget)
        self.setCentralWidget(self.tab_view)

        # Setup Actions
        self.setupActions()

        #  window geometry
        self.resize(600, 400)

        self.addView()
        self.import_vcf("exemples/test.vcf")

    def import_vcf(self, filename):  #  Temporary .. will be removed
        db_filename = filename + ".db"

        if os.path.exists(db_filename):
            os.remove(db_filename)

        self.conn = sqlite3.connect(db_filename)
        import_file(self.conn, filename)

        self.conn.close()
        self.open(db_filename)

    def open(self, db_filename):

        if not os.path.exists(db_filename):
            QMessageBox.warning(self, "error", "file doesn't exists")
            return

        self.conn = sqlite3.connect(db_filename)
        query = Query(self.conn)
        query.filter = json.loads(
            """{"AND" : [{"field":"pos", "operator":">", "value":"880000"} ]}"""
        )

        query.create_selection("mytest")
        # query.filter = None

        self.router.setQuery(query)

    def addPanel(self, widget, area=Qt.LeftDockWidgetArea):
        dock = QDockWidget()
        dock.setWindowTitle(widget.windowTitle())
        dock.setWidget(widget)
        self.addDockWidget(area, dock)

    def setupActions(self):
        fileMenu = self.menuBar().addMenu("&File")
        fileMenu.addAction("&New ...")
        fileMenu.addAction("&Open")

    def addView(self):
        widget = ViewQueryWidget()
        self.view_widgets.append(widget)
        self.tab_view.addTab(widget, widget.windowTitle())
        self.router.addWidget(widget)

    def currentView(self):
        index = self.tab_view.currentIndex()
        if index == -1:
            return None
        return self.view_widgets[index]
