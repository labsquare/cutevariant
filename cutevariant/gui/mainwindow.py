# Standard imports
import sqlite3
import json
import os
import glob
import importlib

# Qt imports
from PySide2.QtCore import *
from PySide2.QtWidgets import *
from PySide2.QtGui import *

# Custom imports
from cutevariant.gui.wizard.projetwizard import ProjetWizard
from cutevariant.gui.settings import SettingsWidget
from cutevariant.gui.viewquerywidget import ViewQueryWidget
from cutevariant.gui.columnquerywidget import ColumnQueryWidget
from cutevariant.gui.filterquerywidget import FilterQueryWidget
from cutevariant.gui.selectionquerywidget import SelectionQueryWidget
from cutevariant.gui.hpoquerywidget import HpoQueryWidget
from cutevariant.gui.vqleditor import VqlEditor
from cutevariant.gui.omnibar import OmniBar
from cutevariant.gui.queryrouter import QueryRouter
from cutevariant.gui.infovariantwidget import InfoVariantWidget
from cutevariant.gui.aboutcutevariant import AboutCutevariant


# testing
from cutevariant.gui.chartquerywidget import ChartQueryWidget
from cutevariant.gui.webglquerywidget import WebGLQueryWidget

from cutevariant.core.importer import import_file
from cutevariant.core import Query
from cutevariant.gui.ficon import FIcon
from cutevariant.gui.plugin import VariantPluginWidget, QueryPluginWidget

# from cutevariant.gui.plugins.infovariantplugin import InfoVariantPlugin

from cutevariant import commons as cm
from cutevariant.commons import MAX_RECENT_PROJECTS, DIR_ICONS

LOGGER = cm.logger()


class MainWindow(QMainWindow):
    def __init__(self, parent=None):

        super(MainWindow, self).__init__()
        self.setWindowTitle("Cutevariant")
        self.toolbar = self.addToolBar("maintoolbar")
        self.toolbar.setObjectName("maintoolbar")  # For window saveState
        self.setWindowIcon(QIcon(DIR_ICONS + "app.png"))

        # keep sqlite connection
        self.conn = None
        # list of central view

        # Keep list of plugins
        self.variant_plugins = []

        # mandatory query plugins
        self.column_widget = ColumnQueryWidget()
        self.filter_widget = FilterQueryWidget()
        self.selection_widget = SelectionQueryWidget()
        self.editor = VqlEditor()
        self.info_widget = InfoVariantWidget()
        # Init router to dispatch query between queryPlugins
        self.router = QueryRouter()
        # Setup Actions
        self.setupActions()
        # Build central view
        self.tab_view = QTabWidget()
        vsplit = QSplitter(Qt.Vertical)
        vsplit.addWidget(self.tab_view)
        vsplit.addWidget(self.editor)
        self.setCentralWidget(vsplit)
        self.router.addWidget(self.editor)
        self.addView()

        # add mandatory query plugin
        self.add_query_plugin(self.column_widget)
        self.add_query_plugin(self.filter_widget)
        self.add_query_plugin(self.selection_widget)

        #testing
        self.add_query_plugin(ChartQueryWidget())
        self.add_query_plugin(WebGLQueryWidget())

        # Add mandatory variant plugin
        self.add_variant_plugin(self.info_widget)


        # Status Bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # # add omnibar
        # self.omnibar = OmniBar()
        # self.toolbar.addSeparator()
        # spacer = QWidget()
        # spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        # self.toolbar.addWidget(spacer)
        # self.toolbar.addWidget(self.omnibar)

        # self.currentView().variant_clicked.connect(self.test.set_variant)
        # self.currentView().variant_clicked.connect(self.test2.set_variant)

        #  window geometry
        self.resize(600, 400)
        self.open("/home/sacha/Dev/cutevariant/examples/test.db")
        self.setGeometry(qApp.desktop().rect().adjusted(100, 100, -100, -100))

        self.load_plugins()
        # Restores the state of this mainwindow's toolbars and dockwidgets
        self.read_settings()

    def add_variant_plugin(self, plugin: VariantPluginWidget):
        # TODO : self current view must send signal only for visable widget 
        self.currentView().variant_clicked.connect(plugin.set_variant)
        self.addPanel(plugin)

    def add_query_plugin(self, plugin: QueryPluginWidget):
        self.router.addWidget(plugin)
        self.addPanel(plugin)

    def load_plugins(self, folder_path = None):
        # TODO ... Load plugins from path. 
        # What is a plugin ? A file or a module folder ? 
        pass 


    def open(self, filepath):
        """Open the given db/project file

        .. note:: Called at the end of a project creation by the Wizard,
            and by Open/Open recent projects slots.

        :param filepath: Path of project file.
        :type filepath: <str>
        """

        if not os.path.exists(filepath):
            return

        # Show the project name in title
        self.setWindowTitle(f"Cutevariant - %s" % os.path.basename(filepath))

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

        self.router.query = query

        # Refresh recent opened projects
        self.adjust_recent_projects(filepath)

        self.setWindowTitle(filepath)
        self.status_bar.showMessage(f"{filepath} opened")

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
        recent_projects = (
            recent_projects
            if len(recent_projects) <= MAX_RECENT_PROJECTS
            else recent_projects[:-1]
        )

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
        # Set the objectName for a correct restoration after saveState
        dock.setObjectName(widget.objectName())
        if not widget.objectName():
            LOGGER.debug(
                "MainWindow:addPanel:: widget '%s' has no objectName attribute"
                "and will not be saved/restored",
                widget.windowTitle(),
            )
        self.addDockWidget(area, dock)
        self.view_menu.addAction(dock.toggleViewAction())

    def setupActions(self):
        # Menu bar
        ## File Menu
        self.file_menu = self.menuBar().addMenu(self.tr("&File"))
        new_prj_action = self.file_menu.addAction(
            FIcon(0xf415),
            self.tr("&New project"),
            self,
            SLOT("new_project()"),
            QKeySequence.New,
        )
        open_prj_action = self.file_menu.addAction(
            FIcon(0xf76f),
            self.tr("&Open project ..."),
            self,
            SLOT("open_project()"),
            QKeySequence.Open,
        )
        ### Recent projects
        self.recent_files_menu = self.file_menu.addMenu(self.tr("Open recent"))

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
        self.file_menu.addAction(
            FIcon(0xF493), self.tr("Settings ..."), self, SLOT("show_settings()")
        )

        self.file_menu.addSeparator()
        self.file_menu.addAction(
            self.tr("&Quit"), qApp, SLOT("quit()"), QKeySequence.Quit
        )

        ## Edit 
        self.edit_menu = self.menuBar().addMenu(self.tr("&Edit"))
        self.edit_menu.addAction(FIcon(0xf18f),"&Copy", self, SLOT("copy()"), QKeySequence.Copy)
        self.edit_menu.addAction(FIcon(0xf192),"&Paste", self, SLOT("paste()"), QKeySequence.Paste)
        self.edit_menu.addSeparator()
        self.edit_menu.addAction(FIcon(0xf486), "Select all", self, SLOT("select_all()"), QKeySequence.SelectAll)

        ## View
        self.view_menu = self.menuBar().addMenu(self.tr("&View"))
        self.view_menu.addAction(
            self.tr("Reset widgets positions"), self, SLOT("reset_ui()")
        )
        self.view_menu.addSeparator()

        ## Help
        self.help_menu = self.menuBar().addMenu(self.tr("Help"))
        self.help_menu.addAction(self.tr("About Qt"), qApp, SLOT("aboutQt()"))
        self.help_menu.addAction(
            self.tr("About Cutevariant"), self, SLOT("aboutCutevariant()")
        )

        # Tool bar
        self.toolbar.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.toolbar.addAction(new_prj_action)
        self.toolbar.addAction(open_prj_action)
        self.toolbar.addSeparator()
    
        save_query_action = self.toolbar.addAction(FIcon(0xf412),self.tr("save query"))
        save_query_action.triggered.connect(self.selection_widget.save_current_query)

    def addView(self):
        #  TODO : manage multiple view
        widget = ViewQueryWidget()
        self.tab_view.addTab(widget, widget.windowTitle())
        self.router.addWidget(widget)

    def currentView(self):
        index = self.tab_view.currentIndex()
        if index == -1:
            return None
        return self.tab_view.currentWidget()

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
            self,
            self.tr("Open project"),
            last_directory,
            self.tr("Cutevariant project (*.db)"),
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
        widget.exec()

    @Slot()
    def aboutCutevariant(self):
        dialog_window = AboutCutevariant()
        dialog_window.exec()

    @Slot()
    def reset_ui(self):
        """Reset the position of docks to the state of the previous launch"""
        # Set reset ui boolean (used by closeEvent)
        self.requested_reset_ui = True

        # Restore docks
        app_settings = QSettings()
        self.restoreState(QByteArray(app_settings.value("windowState")))


    @Slot()
    def copy(self):
        pass

    @Slot()
    def paste(self):
        pass

    @Slot()
    def select_all(self):
        pass

    def closeEvent(self, event):
        """Save the current state of this mainwindow's toolbars and dockwidgets

        .. warning:: Make sure that the property objectName is unique for each
            QToolBar and QDockWidget added to the QMainWindow.

        .. note:: Reset windowState if asked.
        """
        app_settings = QSettings()

        if self.requested_reset_ui:
            # Delete window state setting
            app_settings.remove("windowState")
        else:
            app_settings.setValue("geometry", self.saveGeometry())
            #  TODO: handle UI changes by passing UI_VERSION to saveState()
            app_settings.setValue("windowState", self.saveState())

        super().closeEvent(event)

    def read_settings(self):
        """Restore the state of this mainwindow's toolbars and dockwidgets

        .. note:: If windowState is not stored, current state is written.
        """
        # Init reset ui boolean
        self.requested_reset_ui = False

        app_settings = QSettings()
        self.restoreGeometry(QByteArray(app_settings.value("geometry")))
        #  TODO: handle UI changes by passing UI_VERSION to saveState()
        window_state = app_settings.value("windowState")
        if window_state:
            self.restoreState(QByteArray(window_state))
        else:
            # Setting has been deleted: set the current default state
            #  TODO: handle UI changes by passing UI_VERSION to saveState()
            app_settings.setValue("windowState", self.saveState())
