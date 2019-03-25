from PySide2.QtCore import *
from PySide2.QtWidgets import *
from PySide2.QtGui import *
import sqlite3
import json
import os

from cutevariant.gui.wizard.projetwizard import ProjetWizard
from cutevariant.gui.settings import SettingsWidget
from cutevariant.gui.viewquerywidget import ViewQueryWidget
from cutevariant.gui.columnquerywidget import ColumnQueryWidget
from cutevariant.gui.filterquerywidget import FilterQueryWidget
from cutevariant.gui.selectionquerywidget import SelectionQueryWidget
from cutevariant.gui.hpoquerywidget import HpoQueryWidget
from cutevariant.gui.vqleditor import VqlEditor

from cutevariant.gui.queryrouter import QueryRouter

from cutevariant.core.importer import import_file
from cutevariant.core import Query

from cutevariant.gui.plugins.infovariantplugin import InfoVariantPlugin



class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__()
        self.toolbar = self.addToolBar("maintoolbar")
        self.conn = None
        self.view_widgets = []
        self.column_widget = ColumnQueryWidget()
        self.filter_widget = FilterQueryWidget()
        self.selection_widget = SelectionQueryWidget()
        self.tab_view = QTabWidget()
        self.editor = VqlEditor()



        # Setup Actions
        self.setupActions()

        # Init router
        self.router = QueryRouter()
        # self.router.addWidget(self.view_widget)
        self.router.addWidget(self.column_widget)
        self.router.addWidget(self.filter_widget)
        self.router.addWidget(self.selection_widget)
        self.router.addWidget(self.editor)

     

        vsplit = QSplitter(Qt.Vertical)
        vsplit.addWidget(self.tab_view)
        vsplit.addWidget(self.editor)

        self.setCentralWidget(vsplit)


        # self.test = InfoVariantPlugin()
        # self.test2 = GenomeView()

        #  Init panel
        self.addPanel(self.column_widget)
        self.addPanel(self.filter_widget)
        self.addPanel(self.selection_widget)
        # self.addPanel(self.test)
        # self.addPanel(self.test2)

        #self.addPanel(HpoQueryWidget())

        self.addView()


        # self.currentView().variant_clicked.connect(self.test.set_variant)
        # self.currentView().variant_clicked.connect(self.test2.set_variant)


        #  window geometry
        self.resize(600, 400)

        # self.import_vcf("/home/schutz/Dev/CuteVariant-python/exemples/test.snp.eff.vcf")

        #self.open("/home/schutz/Dev/CuteVariant-python/exemples/test.snpeff.vcf.db")

        self.setGeometry(qApp.desktop().rect().adjusted(100, 100, -100, -100))




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
        # query.filter = json.loads(
        #     """{"AND" : [{"field":"pos", "operator":">", "value":"880000"} ]}"""
        # )

        # query.create_selection("mytest")
        # query.filter = None

        self.router.setQuery(query)

    def addPanel(self, widget, area=Qt.LeftDockWidgetArea):
        dock = QDockWidget()
        dock.setWindowTitle(widget.windowTitle())
        dock.setWidget(widget)
        self.addDockWidget(area, dock)
        self.view_menu.addAction(dock.toggleViewAction())


    def setupActions(self):
        # menu bar 
        self.file_menu = self.menuBar().addMenu("&File")
        self.file_menu.addAction("&New project", self, SLOT("new_project()"), QKeySequence.New)
        self.file_menu.addAction("&Open project ...", self, SLOT("open_project()"), QKeySequence.Open)
        self.file_menu.addSeparator()
        self.file_menu.addAction("Settings ...", self, SLOT("show_settings()"))

        self.view_menu = self.menuBar().addMenu("&View")

        self.help_menu = self.menuBar().addMenu("Help")
        self.help_menu.addAction("About Qt", qApp, SLOT("aboutQt()"))

        # Tool bar

        save_query_action = self.toolbar.addAction("save query")
        save_query_action.triggered.connect(self.selection_widget.save_current_query)

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

    @Slot()
    def new_project(self):
        wizard = ProjetWizard()
        if wizard.exec_():
            db_filename = (
                wizard.field("project_path")
                + QDir.separator()
                + wizard.field("project_name")
                + ".db"
            )
            self.open(db_filename)

    @Slot()
    def open_project(self):
        filename = QFileDialog.getOpenFileName(self,"Open project", "Cutevariant project (*.db)")[0]
        if filename is not None:
            self.open(filename)




    @Slot()
    def show_settings(self):
        widget = SettingsWidget()
        widget.exec_()
