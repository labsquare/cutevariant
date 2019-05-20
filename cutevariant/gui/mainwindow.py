"""Main window of Cutevariant"""
# Standard imports
import os

# Qt imports
from PySide2.QtCore import Qt, QSettings, QByteArray, QDir
from PySide2.QtWidgets import *
from PySide2.QtGui import QIcon, QKeySequence

# Custom imports
from cutevariant.core import Query, get_sql_connexion
from cutevariant.gui.ficon import FIcon
from cutevariant.gui.plugin import VariantPluginWidget, QueryPluginWidget
from cutevariant.gui.wizards import ProjectWizard
from cutevariant.gui.settings import SettingsWidget
from cutevariant.gui.viewquerywidget import ViewQueryWidget
from cutevariant.gui.columnquerywidget import ColumnQueryWidget
from cutevariant.gui.filterquerywidget import FilterQueryWidget
from cutevariant.gui.selectionquerywidget import SelectionQueryWidget
from cutevariant.gui.vqleditor import VqlEditor
from cutevariant.gui.querydispatcher import QueryDispatcher
from cutevariant.gui.infovariantwidget import InfoVariantWidget
from cutevariant.gui.aboutcutevariant import AboutCutevariant
from cutevariant.gui.chartquerywidget import ChartQueryWidget
from cutevariant import commons as cm
from cutevariant.commons import MAX_RECENT_PROJECTS, DIR_ICONS

# Proof of concept - testing only
from cutevariant.gui.webglquerywidget import WebGLQueryWidget
from cutevariant.gui.hpoquerywidget import HpoQueryWidget
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

        # Init QueryDispatcher to dispatch current query to:
        # - QueryPlugins
        # - VqlEditor
        self.query_dispatcher = QueryDispatcher()

        # Build central view based on QTabWidget
        # PS: get current view via current_tab_view()
        # Central widget encapsulates a QTabWidget and VqlEditor
        self.editor = VqlEditor()
        view_query_widget = ViewQueryWidget()

        self.tab_view = QTabWidget()
        vsplit = QSplitter(Qt.Vertical)
        vsplit.addWidget(self.tab_view)  # add QTabWidget
        vsplit.addWidget(self.editor)  # add VqlEditor
        self.setCentralWidget(vsplit)
        # Manually add query_dispatcher to VqlEditor
        self.query_dispatcher.addWidget(self.editor)
        # Add ViewQueryWidget to the QTabWidget
        self.add_tab_view(view_query_widget)
        # TODO: add other tabs here

        # Setup menubar
        self.setup_menubar()

        # Build mandatory plugins that require QueryDispatcher and menubar
        self.column_widget = ColumnQueryWidget()
        self.filter_widget = FilterQueryWidget()
        self.selection_widget = SelectionQueryWidget()
        # Add mandatory query plugins to QDockWidgets
        self.add_query_plugin(self.column_widget)
        self.add_query_plugin(self.filter_widget)
        self.add_query_plugin(self.selection_widget)
        # Testing
        # self.add_query_plugin(ChartQueryWidget())
        # self.add_query_plugin(WebGLQueryWidget())
        # self.add_query_plugin(HpoQueryWidget())

        # Setup toolbar (requires selection_widget and some actions of menubar)
        self.setup_toolbar()

        # Add mandatory variant plugin (depends on QTabWidget and menubar)
        self.info_widget = InfoVariantWidget()
        self.add_variant_plugin(self.info_widget)

        # Status Bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # Add omnibar
        # self.omnibar = OmniBar()
        # self.toolbar.addSeparator()
        # spacer = QWidget()
        # spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        # self.toolbar.addWidget(spacer)
        # self.toolbar.addWidget(self.omnibar)

        # Window geometry
        self.resize(600, 400)
        self.setGeometry(qApp.desktop().rect().adjusted(100, 100, -100, -100))

        # Load external plugins
        self.load_plugins()

        # Restores the state of this mainwindow's toolbars and dockwidgets
        self.read_settings()

        # Display messages from plugins in the status bar
        self.editor.message.connect(self.handle_plugin_message)
        view_query_widget.message.connect(self.handle_plugin_message)

        self.open("examples/test2.db")

    def add_variant_plugin(self, plugin: VariantPluginWidget):
        """Add info variant plugin to QDockWidget

        .. note:: This plugin doesn't require query_dispatcher
        .. TODO:: current tab view must send signal only for visible widget
        """
        # Connect click event on a variant in ViewQueryWidget
        # => update InfoVariantWidget
        self.current_tab_view().variant_clicked.connect(plugin.set_variant)
        self.add_panel(plugin)

    def add_query_plugin(self, plugin: QueryPluginWidget):
        """Add query plugin to QDockWidget and connect it to query_dispatcher"""
        self.query_dispatcher.addWidget(plugin)
        self.add_panel(plugin)
        plugin.message.connect(self.handle_plugin_message)

    def load_plugins(self, folder_path=None):
        """TODO ... Load plugins from path.
        What is a plugin ? A file or a module folder ?
        """
        pass

    def add_panel(self, widget, area=Qt.LeftDockWidgetArea):
        """Add given widget to a new QDockWidget and to view menu in menubar"""
        dock = QDockWidget()
        dock.setWindowTitle(widget.windowTitle())
        dock.setWidget(widget)

        # Set the objectName for a correct restoration after saveState
        dock.setObjectName(widget.objectName())
        if not widget.objectName():
            LOGGER.debug(
                "MainWindow:add_panel:: widget '%s' has no objectName attribute"
                "and will not be saved/restored",
                widget.windowTitle(),
            )
        self.addDockWidget(area, dock)
        self.view_menu.addAction(dock.toggleViewAction())

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
        self.toolbar.addSeparator()

        self.toolbar.addAction(
            FIcon(0xF412),
            self.tr("Save query"),
            self.selection_widget.save_current_query,
        )

        self.toolbar.addAction(
            FIcon(0xF40D), self.tr("Run"), self.editor.run_vql
        ).setShortcuts([Qt.CTRL + Qt.Key_R, QKeySequence.Refresh])

    def add_tab_view(self, widget):
        """Add the given widget to the current (QTabWidget),
        and connect it to the query_dispatcher"""
        self.tab_view.addTab(widget, widget.windowTitle())
        self.query_dispatcher.addWidget(widget)

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
        self.status_bar.showMessage(self.tr("{filepath} opened"))

        # Save directory
        app_settings = QSettings()
        app_settings.setValue("last_directory", os.path.dirname(filepath))

        # Create connection
        self.conn = get_sql_connexion(filepath)

        # Create a query
        query = Query(self.conn)

        # Dispatch the query to all widget from the router
        self.query_dispatcher.query = query

        # Update all widgets
        self.query_dispatcher.update_all_widgets()

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

    def open_recent(self):
        """Slot to load a recent project"""
        action = self.sender()
        self.open(action.data())

    def clear_recent_projects(self):
        """Slot to clear the list of recent projects"""
        app_settings = QSettings()
        app_settings.remove("recent_projects")
        self.update_recent_projects_actions()

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
