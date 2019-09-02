"""Main window of Cutevariant"""
# Standard imports
import os
import sys
import importlib
import glob

# Qt imports
from PySide2.QtCore import Qt, QSettings, QByteArray, QDir, Slot
from PySide2.QtWidgets import *
from PySide2.QtGui import QIcon, QKeySequence

# Custom imports
from cutevariant.core import Query, get_sql_connexion
from cutevariant.gui.ficon import FIcon
from cutevariant.gui.wizards import ProjectWizard
from cutevariant.gui.settings import SettingsWidget
from cutevariant.gui.querywidget import QueryWidget
from cutevariant.gui import plugin

#  Import plugins
from cutevariant.gui.plugins.editor.plugin import EditorPlugin

from cutevariant.gui.aboutcutevariant import AboutCutevariant
# from cutevariant.gui.chartquerywidget import ChartQueryWidget
from cutevariant import commons as cm
from cutevariant.commons import MAX_RECENT_PROJECTS, DIR_ICONS

# Proof of concept - testing only
# from cutevariant.gui.webglquerywidget import WebGLQueryWidget
# from cutevariant.gui.hpoquerywidget import HpoQueryWidget

# from cutevariant.gui.omnibar import OmniBar


LOGGER = cm.logger()


class MainWindow(QMainWindow):
    def __init__(self, parent=None):

        super(MainWindow, self).__init__()
        self.setWindowTitle("Cutevariant")
        self.toolbar = self.addToolBar("maintoolbar")
        self.toolbar.setObjectName("maintoolbar")  # For window saveState
        self.setWindowIcon(QIcon(DIR_ICONS + "app.png"))

        # Keep sqlite connection
        self.conn = None

        # store dock plugins
        self.plugins = []

        # Build central view based on QTabWidget
        # PS: get current view via current_tab_view()
        # Central widget encapsulates a QTabWidget and VqlEditor
        self.query_widget = QueryWidget()
        self.central_tab = QTabWidget()

        #  create editor plugins
        self.editor_plugin = EditorPlugin(self)
        self.editor = self.editor_plugin.get_widget()

        vsplit = QSplitter(Qt.Vertical)
        vsplit.addWidget(self.central_tab)  # add QTabWidget
        vsplit.addWidget(self.editor)  # add VqlEditor
        self.setCentralWidget(vsplit)
        self.add_tab_view(self.query_widget)
        # TODO: add other tabs here

        # Setup menubar
        self.setup_menubar()
        self.setup_toolbar()

        # Status Bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)  

        # registere editor plugins
        self.register_plugin(self.editor_plugin)

        #  register other plugins
        for PluginClass in plugin.find_plugins():
            # Note : passing self is important to make the plugin workable
            self.register_plugin(PluginClass(self))

        # Window geometry
        self.resize(600, 400)
        self.setGeometry(qApp.desktop().rect().adjusted(100, 100, -100, -100))

        # Restores the state of this mainwindow's toolbars and dockwidgets
        self.read_settings()

        #self.open("test.db")

    def add_panel(self, widget, area=Qt.LeftDockWidgetArea):
        """Add given widget to a new QDockWidget and to view menu in menubar"""
        dock = QDockWidget()
        dock.setWindowTitle(widget.windowTitle())
        dock.setWidget(widget)

        # Set the objectName for a correct restoration after saveState
        dock.setObjectName(str(widget.__class__))
        if not widget.objectName():
            LOGGER.debug(
                "MainWindow:add_panel:: widget '%s' has no objectName attribute"
                "and will not be saved/restored",
                widget.windowTitle(),
            )
        self.addDockWidget(area, dock)
        self.view_menu.addAction(dock.toggleViewAction())

    def register_plugin(self, plugin: plugin.Plugin):
        """add plugin to the application
        
        Arguments:
            plugin plugin.Plugin
        """

        self.plugins.append(plugin)

        # call abstract method 
        plugin.on_register()

        # connect variant clicked signal with the plugin
        self.query_widget.variant_clicked.connect(plugin.on_variant_clicked)

        # connect variant model with the plugin
        self.query_widget.model.changed.connect(plugin.on_query_model_changed)

        #  Add dockable widget if it's required
        widget = plugin.get_widget()
        if widget is not None:
            if plugin.dockable:
                self.add_panel(widget)

   

    def setup_menubar(self):
        """Menu bar setup: items and actions"""
        ## File Menu
        self.file_menu = self.menuBar().addMenu(self.tr("&File"))
        self.new_project_action = self.file_menu.addAction(
            FIcon(0xF415), self.tr("&New project"), self.new_project, QKeySequence.New
        )
        self.open_project_action = self.file_menu.addAction(
            FIcon(0xF76F),
            self.tr("&Open project ..."),
            self.open_project,
            QKeySequence.Open,
        )
        ### Recent projects
        self.recent_files_menu = self.file_menu.addMenu(self.tr("Open recent"))

        self.setup_recent_menu()
       
        self.recent_files_menu.addSeparator()
        self.recent_files_menu.addAction(self.tr("Clear"), self.clear_recent_projects)

        self.file_menu.addSeparator()
        self.file_menu.addAction(
            FIcon(0xF493), self.tr("Settings ..."), self.show_settings
        )

        self.file_menu.addSeparator()
        self.file_menu.addAction(self.tr("&Quit"), qApp.quit, QKeySequence.Quit)

        ## Edit
        self.edit_menu = self.menuBar().addMenu(self.tr("&Edit"))
        self.edit_menu.addAction(FIcon(0xF18F), "&Copy", self.copy, QKeySequence.Copy)
        self.edit_menu.addAction(
            FIcon(0xF192), "&Paste", self.paste, QKeySequence.Paste
        )
        self.edit_menu.addSeparator()
        self.edit_menu.addAction(
            FIcon(0xF486), "Select all", self.select_all, QKeySequence.SelectAll
        )

        ## View
        self.view_menu = self.menuBar().addMenu(self.tr("&View"))
        self.view_menu.addAction(self.tr("Reset widgets positions"), self.reset_ui)
        console_action = self.view_menu.addAction(FIcon(0xf18d),self.tr("Show console"))
        console_action.setCheckable(True)
        console_action.setShortcuts([Qt.CTRL + Qt.Key_T])
        console_action.toggled.connect(self.editor.setVisible)
        
        self.view_menu.addSeparator()

        ## Help
        self.help_menu = self.menuBar().addMenu(self.tr("Help"))
        self.help_menu.addAction(self.tr("About Qt"), qApp.aboutQt)
        self.help_menu.addAction(self.tr("About Cutevariant"), self.aboutCutevariant)

    def setup_toolbar(self):
        """Tool bar setup: items and actions

        .. note:: Require selection_widget and some actions of Menubar
        """
        # Tool bar
        self.toolbar.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.toolbar.addAction(self.new_project_action)
        self.toolbar.addAction(self.open_project_action)
        self.toolbar.addAction(FIcon(0xF40A),"Run", self.execute_vql).setShortcuts([Qt.CTRL + Qt.Key_R, QKeySequence.Refresh])
        self.toolbar.addSeparator()

    def add_tab_view(self, widget):
        """Add the given widget to the current (QTabWidget),
        and connect it to the query_dispatcher"""
        self.central_tab.addTab(widget, widget.windowTitle())
        # self.query_dispatcher.addWidget(widget)

    def current_tab_view(self):
        """Get the page/tab currently being displayed by the tab dialog

        :return: Return the current tab in the QTabWidget
        :rtype: <QWidget>
        """
        # Get the index position of the current tab page
        index = self.tab_view.currentIndex()
        if index == -1:
            # No tab in the widget
            return None
        return self.tab_view.currentWidget()

    def open(self, filepath):
        """Open the given db/project file

        .. note:: Called at the end of a project creation by the Wizard,
            and by Open/Open recent projects slots.

        :param filepath: Path of project file.
        :type filepath: <str>
        """
        if not os.path.exists(filepath):
            return

        # Show the project name in title and in status bar
        self.setWindowTitle("Cutevariant - %s" % os.path.basename(filepath))
        self.status_bar.showMessage(self.tr("{} opened").format(filepath))

        # Save directory
        app_settings = QSettings()
        app_settings.setValue("last_directory", os.path.dirname(filepath))

        # Create connection
        self.conn = get_sql_connexion(filepath)

        # Create central view 
        # TODO: rename the class 
        self.query_widget.conn = self.conn
        self.query_widget.model.load()

        for plugin in self.plugins:
            plugin.on_open_project(self.conn)

        self.save_recent_project(filepath)

    def save_recent_project(self, path):
        """Save current project into QSettings
        
        Args:
            path (str): path of project
        """
        paths = list(self.get_recent_projects())
        paths.insert(0, path)
        app_settings = QSettings()
        unique_paths = list(dict.fromkeys(paths))
        app_settings.setValue("recent_projects", unique_paths[:MAX_RECENT_PROJECTS])

    def get_recent_projects(self):
        """Return the list of recent projects stored in settings
        
        Returns:
            list: Return list of recent project path
        """
    
        # Reload last projects opened
        app_settings = QSettings()
        recent_projects = app_settings.value("recent_projects", list())

        # Check if recent_projects is a list() (as expected)
        if isinstance(recent_projects, str):
            recent_projects = [recent_projects]

        return recent_projects

    def clear_recent_projects(self):
        """Slot to clear the list of recent projects"""
        app_settings = QSettings()
        app_settings.remove("recent_projects")
        self.setup_recent_menu()

    def setup_recent_menu(self):
        """ Setup recent menu """
        self.recent_files_menu.clear()
        for path in self.get_recent_projects():
            self.recent_files_menu.addAction(path,self.on_recent_project_clicked)

    def on_recent_project_clicked(self):
        """Slot to load a recent project"""
        action = self.sender()
        self.open(action.text())


    def handle_plugin_message(self, message):
        """Slot to display message from plugin in the status bar"""
        self.status_bar.showMessage(message)

    def new_project(self):
        """Slot to allow creation of a project with the Wizard"""
        wizard = ProjectWizard()
        if wizard.exec_():
            db_filename = (
                wizard.field("project_path")
                + QDir.separator()
                + wizard.field("project_name")
                + ".db"
            )
            try:
                self.open(db_filename)
            except Exception as e:
                self.status_bar.showMessage(e.__class__.__name__ + ": " + str(e))
                raise

    def open_project(self):
        """Slot to open an already existing project"""
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
            try:
                self.open(filepath)
            except Exception as e:
                self.status_bar.showMessage(e.__class__.__name__ + ": " + str(e))
                raise
    

    def show_settings(self):
        """Slot to show settings window"""
        widget = SettingsWidget()
        widget.exec()

    def aboutCutevariant(self):
        """Slot to show about window"""
        dialog_window = AboutCutevariant()
        dialog_window.exec()

    def reset_ui(self):
        """Slot to reset the position of docks to the state of the previous launch"""
        # Set reset ui boolean (used by closeEvent)
        self.requested_reset_ui = True

        # Restore docks
        app_settings = QSettings()
        self.restoreState(QByteArray(app_settings.value("windowState")))

    def copy(self):
        pass

    def paste(self):
        pass

    def select_all(self):
        """Select all elements in the current tab's view"""
        self.current_tab_view().view.selectAll()

    def closeEvent(self, event):
        """Save the current state of this mainwindow's toolbars and dockwidgets

        .. warning:: Make sure that the property objectName is unique for each
            QToolBar and QDockWidget added to the QMainWindow.

        .. note:: Reset windowState if asked.
        """
        self.write_settings()
        super().closeEvent(event)

    def write_settings(self):
        """ Store the state of this mainwindow. 

        .. note:: This methods is called by closeEvent 
        """
        app_settings = QSettings()

        if self.requested_reset_ui:
            # Delete window state setting
            app_settings.remove("windowState")
        else:
            app_settings.setValue("geometry", self.saveGeometry())
            #  TODO: handle UI changes by passing UI_VERSION to saveState()
            app_settings.setValue("windowState", self.saveState())



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

    @Slot()
    def execute_vql(self):
        """ Execute query from editor """
        self.editor.run_vql()


if __name__ == "__main__":
    app = QApplication(sys.argv)

    w = MainWindow()

    w.show()

    app.exec_()
