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
from cutevariant.gui.ficon import FIcon

from cutevariant.gui.plugins.infovariantplugin import InfoVariantPlugin

from cutevariant.commons import MAX_RECENT_PROJECTS


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__()
        self.setWindowTitle("Cutevariant")
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

        # self.addPanel(HpoQueryWidget())

        self.addView()

        # self.currentView().variant_clicked.connect(self.test.set_variant)
        # self.currentView().variant_clicked.connect(self.test2.set_variant)

        #  window geometry
        self.resize(600, 400)

        # self.import_vcf("/home/schutz/Dev/CuteVariant-python/exemples/test.snp.eff.vcf")

        self.open("/home/sacha/Dev/cutevariant/examples/test.db")

        self.setGeometry(qApp.desktop().rect().adjusted(100, 100, -100, -100))

    def import_vcf(self, filename):  #  Temporary .. will be removed
        db_filename = filename + ".db"

        if os.path.exists(db_filename):
            os.remove(db_filename)

        self.conn = sqlite3.connect(db_filename)
        import_file(self.conn, filename)

        self.conn.close()
        self.open(db_filename)

    def open(self, filepath):
        """Open the given db/project file

        .. note:: Called at the end of a project creation by the Wizard,
            and by Open/Open recent projects slots.

        :param filepath: Path of project file.
        :type filepath: <str>
        """

        if not os.path.exists(filepath):
            return

        # Save directory
        app_settings = QSettings()
        app_settings.setValue("last_directory", os.path.dirname(filepath))

        self.conn = sqlite3.connect(filepath)
        query = Query(self.conn)
        # query.filter = json.loads(
        #     """{"AND" : [{"field":"pos", "operator":">", "value":"880000"} ]}"""
        # )

        # query.create_selection("mytest")
        # query.filter = None

        self.router.setQuery(query)

        # Refresh recent opened projects
        self.adjust_recent_projects(filepath)

    def adjust_recent_projects(self, filepath):
        """Adjust the number of of recent projects to display

        .. note:: Called after a successful file opening.

        :param filepath: Path of project file.
        :type filepath: <str>
        """

        # Get recent projects list
        recent_projects = self.get_recent_projects()

        try:
            recent_projects.remove(filepath)
        except ValueError:
            # New file is not already in the list
            pass
        # Prepend new file
        recent_projects = [filepath] + recent_projects
        recent_projects = \
            recent_projects if len(recent_projects) <= MAX_RECENT_PROJECTS \
            else recent_projects[:-1]

        # Save in settings
        app_settings = QSettings()
        app_settings.setValue("recent_projects", recent_projects)

        # Display
        self.update_recent_projects_actions()

    def update_recent_projects_actions(self):
        """Display recent projects in the menu

        .. note:: Called after a successful file opening and during the launch
            of the software.
        """

        # Get recent projects list
        recent_projects = self.get_recent_projects()

        index = -1
        for index, filepath in enumerate(recent_projects, 0):
            action = self.recentFileActions[index]
            # Get filename
            # TODO: get project name ?
            action.setText(os.path.basename(filepath))
            action.setData(filepath)
            action.setVisible(True)

        # Display the action
        if index == -1:
            self.recent_files_menu.setEnabled(False)
        else:
            self.recent_files_menu.setEnabled(True)

        # Switch off useless actions
        # index = -1 if there is no recent_projects
        index = 0 if index < 0 else index + 1
        for i in range(index, MAX_RECENT_PROJECTS):
            self.recentFileActions[i].setVisible(False)

    def get_recent_projects(self):
        """Return the list of recent projects stored in settings

        :return: List of recent projects.
        :type: <list>
        """
        # Reload last projects opened
        app_settings = QSettings()
        recent_projects = app_settings.value("recent_projects", list())

        # Check if recent_projects is a list() (as expected)
        if isinstance(recent_projects, str):
            recent_projects = [recent_projects]

        return recent_projects

    def addPanel(self, widget, area=Qt.LeftDockWidgetArea):
        dock = QDockWidget()
        dock.setWindowTitle(widget.windowTitle())
        dock.setWidget(widget)
        self.addDockWidget(area, dock)
        self.view_menu.addAction(dock.toggleViewAction())

    def setupActions(self):
        # Menu bar
        ## File Menu
        self.file_menu = self.menuBar().addMenu(self.tr("&File"))
        self.file_menu.addAction(FIcon(0xf214),
            self.tr("&New project"), self, SLOT("new_project()"), QKeySequence.New
        )
        self.file_menu.addAction(
            self.tr("&Open project ..."), self, SLOT("open_project()"), QKeySequence.Open
        )
        ### Recent projects
        self.recent_files_menu = self.file_menu.addMenu(
            self.tr("Open recent")
        )

        self.recentFileActions = list()
        for i in range(MAX_RECENT_PROJECTS):
            new_action = QAction()
            new_action.setVisible(False)
            # Keep actions in memory for their display to be managed later
            self.recentFileActions.append(new_action)
            self.recent_files_menu.addAction(new_action)
            new_action.triggered.connect(self.open_recent)

        # Init previous files
        self.update_recent_projects_actions()

        self.recent_files_menu.addSeparator()
        self.recent_files_menu.addAction(
            self.tr("Clear"), self, SLOT("clear_recent_projects()")
        )

        self.file_menu.addSeparator()
        self.file_menu.addAction(FIcon(0xf493), self.tr("Settings ..."), self, SLOT("show_settings()"))

        self.file_menu.addSeparator()
        self.file_menu.addAction(self.tr("&Quit"), qApp, SLOT("quit()"), QKeySequence.Quit)

        ## View
        self.view_menu = self.menuBar().addMenu(self.tr("&View"))

        ## Help
        self.help_menu = self.menuBar().addMenu(self.tr("Help"))
        self.help_menu.addAction(self.tr("About Qt"), qApp, SLOT("aboutQt()"))

        # Tool bar
        save_query_action = self.toolbar.addAction(self.tr("save query"))
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
        """Create a project with the Wizard"""
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
        """Open a project"""
        # Reload last directory used
        app_settings = QSettings()
        last_directory = app_settings.value("last_directory", QDir.homePath())

        filepath, _ = QFileDialog.getOpenFileName(
            self, self.tr("Open project"), last_directory,
            self.tr("Cutevariant project (*.db)")
        )
        if filepath:
            self.open(filepath)

    @Slot()
    def open_recent(self):
        """Load a recent project"""
        action = self.sender()
        self.open(action.data())

    @Slot()
    def clear_recent_projects(self):
        """Clear the list of recent projects"""
        app_settings = QSettings()
        app_settings.remove("recent_projects")
        self.update_recent_projects_actions()

    @Slot()
    def show_settings(self):
        widget = SettingsWidget()
        widget.exec_()
