"""Main window of Cutevariant"""
# Standard imports
import os
import sys
import sqlite3
from pkg_resources import parse_version
from logging import DEBUG

# Qt imports
from PySide2.QtCore import Qt, QSettings, QByteArray, QDir
from PySide2.QtWidgets import *
from PySide2.QtGui import QIcon, QKeySequence

# Custom imports
from cutevariant.core import get_sql_connexion, get_metadatas, command
from cutevariant.core.writer import CsvWriter
from cutevariant.gui.ficon import FIcon
from cutevariant.gui.state import State
from cutevariant.gui.wizards import ProjectWizard
from cutevariant.gui.settings import SettingsWidget
from cutevariant.gui.widgets.aboutcutevariant import AboutCutevariant
from cutevariant import commons as cm
from cutevariant.commons import (
    MAX_RECENT_PROJECTS,
    DIR_ICONS,
    MIN_AUTHORIZED_DB_VERSION,
)

# Import plugins
from cutevariant.gui import plugin

LOGGER = cm.logger()


class MainWindow(QMainWindow):
    def __init__(self, parent=None):

        super(MainWindow, self).__init__()

        self.setWindowTitle("Cutevariant")
        self.toolbar = self.addToolBar("maintoolbar")
        self.toolbar.setObjectName("maintoolbar")  # For window saveState
        self.setWindowIcon(QIcon(DIR_ICONS + "app.png"))
        self.setWindowFlags(Qt.WindowContextHelpButtonHint)

        # Keep sqlite connection
        self.conn = None

        # State variable of application
        # store fields, source, filters, group_by, having data
        # Often changed by plugins
        self.state = State()

        self.central_tab = QTabWidget()
        self.footer_tab = QTabWidget()

        vsplit = QSplitter(Qt.Vertical)
        vsplit.addWidget(self.central_tab)
        vsplit.addWidget(self.footer_tab)
        self.setCentralWidget(vsplit)

        # Status Bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # Setup menubar
        self.setup_menubar()
        # Setup toobar under the menu bar
        self.setup_toolbar()

        # Register plugins
        self.plugins = {}  # dict of names as keys and widgets as values
        self.dialog_plugins = {}  # dict of actions as keys and classes as values
        self.register_plugins()

        # Window geometry
        self.resize(600, 400)
        self.setGeometry(qApp.desktop().rect().adjusted(100, 100, -100, -100))

        self.setTabPosition(Qt.AllDockWidgetAreas, QTabWidget.North)

        # If True, the GUI settings are deleted when the app is closed
        self.requested_reset_ui = False
        # Restores the state of this mainwindow's toolbars and dockwidgets
        self.read_settings()

        # Auto open recent projects
        recent = self.get_recent_projects()
        if recent and os.path.isfile(recent[0]):
            self.open(recent[0])

    def add_panel(self, widget, area=Qt.LeftDockWidgetArea):
        """Add given widget to a new QDockWidget and to view menu in menubar"""
        dock = QDockWidget()
        dock.setWindowTitle(widget.windowTitle())
        dock.setWidget(widget)
        dock.setStyleSheet("QDockWidget { font: bold }")
        # Keep the attached dock to allow further clean deletion
        widget.dock = dock

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

    def register_plugins(self):
        """Dynamically load plugins to the window

        Two types of plugins can be registered:
        - widget: Added to the GUI,
        - dialog: DialogBox accessible from the tool menu.

        `setting` type is handled separately in :meth:`cutevariant.gui.settings.load_plugins`
        """
        LOGGER.info("MainWindow:: Registering plugins...")

        # Get classes of plugins
        for extension in plugin.find_plugins():
            LOGGER.debug("Extension: %s", extension)

            if "widget" in extension:
                # New GUI widget
                name = extension["name"]
                plugin_widget_class = extension["widget"]

                # Setup new widget
                widget = plugin_widget_class(parent=self)

                # Set title
                if LOGGER.getEffectiveLevel() == DEBUG:
                    widget.setWindowTitle(name)
                else:
                    widget.setWindowTitle(extension["title"])
                # WhatsThis content
                long_description = extension.get("long_description")
                if not long_description:
                    long_description = extension.get("description")
                widget.setWhatsThis(long_description)
                # Register (launch first init on some of them)
                widget.on_register(self)

                # Init mainwindow via the constructor or on_register
                if widget.mainwindow != self:
                    LOGGER.error(
                        "Bad plugin implementation, <mainwindow> plugin attribute is not set."
                    )
                    widget.close()
                    continue

                # Add new plugin to plugins already registered
                self.plugins[name] = widget

                # Set position on the GUI
                if plugin_widget_class.LOCATION == plugin.DOCK_LOCATION:
                    self.add_panel(widget)

                if plugin_widget_class.LOCATION == plugin.CENTRAL_LOCATION:
                    self.central_tab.addTab(widget, widget.windowTitle())

                if plugin_widget_class.LOCATION == plugin.FOOTER_LOCATION:
                    self.footer_tab.addTab(widget, widget.windowTitle())

            if "dialog" in extension:
                # New tool menu entry
                title = extension["title"]
                plugin_dialog_class = extension["dialog"]

                # Add plugin to Tools menu
                dialog_action = self.tool_menu.addAction(title)
                self.dialog_plugins[dialog_action] = plugin_dialog_class
                dialog_action.triggered.connect(self.show_dialog)

    def refresh_plugins(self, sender: plugin.PluginWidget = None):
        """Refresh all plugins except_plugins

        Args:
            sender (PluginWidget): from a plugin, you can pass "self" as argument
        """
        for plugin_obj in self.plugins.values():
            if plugin_obj is not sender and plugin_obj.isVisible():
                try:
                    plugin_obj.on_refresh()
                except Exception as e:
                    LOGGER.error(
                        "{}:{} {}".format(
                            plugin_obj, format(sys.exc_info()[-1].tb_lineno), e
                        )
                    )

    def refresh_plugin(self, plugin_name: str):
        """Refresh a plugin identified by plugin_name
        It doesn't refresh the sender plugin

        Args:
            plugin_name (str): a plugin name.
        """
        if plugin_name in self.plugins:
            plugin_obj = self.plugins[plugin_name]
            plugin_obj.on_refresh()

    def setup_menubar(self):
        """Menu bar setup: items and actions

        .. note:: Setup tools menu that could be dynamically augmented by plugins.
        """
        ## File Menu
        self.file_menu = self.menuBar().addMenu(self.tr("&File"))
        self.new_project_action = self.file_menu.addAction(
            FIcon(0xF01BA), self.tr("&New project"), self.new_project, QKeySequence.New
        )
        self.open_project_action = self.file_menu.addAction(
            FIcon(0xF095D),
            self.tr("&Open project ..."),
            self.open_project,
            QKeySequence.Open,
        )
        ### Recent projects
        self.recent_files_menu = self.file_menu.addMenu(self.tr("Open recent"))
        self.setup_recent_menu()

        ## Export projects as
        self.export_action = self.file_menu.addAction(
            self.tr("Export as csv"), self.export_project
        )

        self.file_menu.addSeparator()
        self.file_menu.addAction(
            FIcon(0xF0493), self.tr("Settings ..."), self.show_settings
        )

        self.file_menu.addSeparator()

        self.file_menu.addSeparator()

        self.file_menu.addSeparator()
        self.file_menu.addAction(self.tr("&Quit"), self.close, QKeySequence.Quit)

        ## Edit
        # TODO: if variant_view plugin is not loaded, disable this menu entries...
        self.edit_menu = self.menuBar().addMenu(self.tr("&Edit"))
        self.edit_menu.addAction(FIcon(0xF018F), "&Copy variants", self.copy_variants_to_clipboard, QKeySequence.Copy)
        # self.edit_menu.addAction(
        #     FIcon(0xF0192), "&Paste", self.paste, QKeySequence.Paste
        # )
        self.edit_menu.addSeparator()
        self.edit_menu.addAction(
            FIcon(0xF0486), "Select all variants", self.select_all_variants, QKeySequence.SelectAll
        )

        ## View
        self.view_menu = self.menuBar().addMenu(self.tr("&View"))
        self.view_menu.addAction(self.tr("Reset widgets positions"), self.reset_ui)
        self.view_menu.addSeparator()

        ## Tools
        self.tool_menu = self.menuBar().addMenu(self.tr("&Tools"))

        ## Help
        self.help_menu = self.menuBar().addMenu(self.tr("Help"))
        self.help_menu.addAction(self.tr("About Qt"), qApp.aboutQt)
        self.help_menu.addAction(
            QIcon(DIR_ICONS + "app.png"),
            self.tr("About Cutevariant"),
            self.aboutCutevariant,
        )
        self.help_menu.addAction(
            FIcon(0xF02D6), self.tr("What's this"), QWhatsThis.enterWhatsThisMode
        )

    def setup_toolbar(self):
        """Tool bar setup: items and actions

        .. note:: Require selection_widget and some actions of Menubar
        """
        # Tool bar
        self.toolbar.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.toolbar.addAction(self.new_project_action)
        self.toolbar.addAction(self.open_project_action)
        self.toolbar.addSeparator()

    def open(self, filepath):
        """Open the given db/project file

        .. note:: Called at the end of a project creation by the Wizard,
            and by Open/Open recent projects slots.

        :param filepath: Path of project file.
        :type filepath: <str>
        """
        if not os.path.isfile(filepath):
            return

        # Save directory
        app_settings = QSettings()
        app_settings.setValue("last_directory", os.path.dirname(filepath))

        # Create connection
        self.conn = get_sql_connexion(filepath)

        # DB version filter
        db_version = get_metadatas(self.conn).get("cutevariant_version")
        if db_version and parse_version(db_version) < parse_version(
            MIN_AUTHORIZED_DB_VERSION
        ):
            # Refuse to open blacklisted DB versions
            # Unversioned files are still accepted
            QMessageBox.critical(
                self,
                self.tr("Error while opening project"),
                self.tr("File: {} is too old; please create a new project.").format(filepath),
            )
            return

        try:
            self.open_database(self.conn)
            self.save_recent_project(filepath)

            # Show the project name in title and in status bar
            self.setWindowTitle("Cutevariant - %s" % os.path.basename(filepath))
            self.status_bar.showMessage(self.tr("{} opened").format(filepath))

        except sqlite3.OperationalError as e:
            LOGGER.error("MainWindow:open:: %s", e)
            QMessageBox.critical(
                self,
                self.tr("Error while opening project"),
                self.tr("File: {}\nThe following exception occurred:\n{}").format(filepath, e),
            )

    def open_database(self, conn):
        """Open the project file and populate widgets

        Args:
            conn (sqlite3.Connection): Sqlite3 Connection
        """
        self.conn = conn

        # Clear memoization cache for count_cmd
        command.clear_cache_cmd()

        for plugin_obj in self.plugins.values():
            plugin_obj.on_open_project(self.conn)

    def save_recent_project(self, path):
        """Save current project into QSettings

        Args:
            path (str): path of project
        """
        paths = self.get_recent_projects()
        if path in paths:
            paths.remove(path)
        paths.insert(0, path)
        app_settings = QSettings()
        app_settings.setValue("recent_projects", paths[:MAX_RECENT_PROJECTS])

    def get_recent_projects(self):
        """Return the list of recent projects stored in settings

        Returns:
            list: Recent project paths
        """

        # Reload last projects opened
        app_settings = QSettings()
        recent_projects = app_settings.value("recent_projects", list())

        # Check if recent_projects is a list() (as expected)
        if isinstance(recent_projects, str):
            recent_projects = [recent_projects]

        # Check if file exists
        recent_projects = [p for p in recent_projects if os.path.exists(p)]

        return recent_projects

    def clear_recent_projects(self):
        """Slot to clear the list of recent projects"""
        app_settings = QSettings()
        app_settings.remove("recent_projects")
        self.setup_recent_menu()

    def setup_recent_menu(self):
        """Setup recent submenu with previously opened projects"""
        self.recent_files_menu.clear()
        for path in self.get_recent_projects():
            self.recent_files_menu.addAction(path, self.on_recent_project_clicked)

        self.recent_files_menu.addSeparator()
        self.recent_files_menu.addAction(self.tr("Clear"), self.clear_recent_projects)

    def on_recent_project_clicked(self):
        """Slot to load a recent project"""
        action = self.sender()
        LOGGER.debug(action.text())
        self.open(action.text())

    def new_project(self):
        """Slot to allow creation of a project with the Wizard"""
        wizard = ProjectWizard()
        if not wizard.exec_():
            return

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
        """Slot to open an already existing project from a QFileDialog"""
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

    def export_project(self):
        """Export variants into CSV file"""
        # Reload last directory used
        app_settings = QSettings()
        last_directory = app_settings.value("last_directory", QDir.homePath())

        filepath, _ = QFileDialog.getSaveFileName(
            self, self.tr("Save project"), last_directory, self.tr("(*.csv)")
        )

        if filepath:
            with open(filepath, "w") as file:
                writer = CsvWriter(file)
                writer.save(self.conn)

    def show_settings(self):
        """Slot to show settings window"""
        widget = SettingsWidget(parent=self)
        widget.uiSettingsChanged.connect(self.reload_ui)
        widget.exec_()

    def show_dialog(self):
        """Show Plugin dialog box after a click on the tool menu"""
        action = self.sender()
        if action in self.dialog_plugins:
            # Get class object and instantiate it
            dialog_class = self.dialog_plugins[action]
            dialog = dialog_class(conn=self.conn)
            # Send SQL connection
            dialog.on_refresh()
            dialog.exec_()

    def aboutCutevariant(self):
        """Slot to show about window"""
        dialog_window = AboutCutevariant()
        dialog_window.exec_()

    def reload_ui(self):
        """Reload *without* reset the positions of the widgets"""
        geometry = self.saveGeometry()
        ui_state = self.saveState()
        self.reset_ui()
        # Reload positions
        self.restoreGeometry(geometry)
        self.restoreState(ui_state)

    def reset_ui(self):
        """Reset the positions of docks (and their widgets) to the default state

        All the widgets are deleted and reinstantiated on the GUI.
        GUI settings via QSettings are also reset.
        """
        # Set reset ui boolean (used by closeEvent)
        self.requested_reset_ui = True
        # Reset settings
        self.write_settings()

        # Remove widgets in QTabWidgets
        self.central_tab.removeTab(0)
        self.footer_tab.removeTab(0)

        # Remove view menu actions linked to the widget plugins (enable/disable)
        for action in self.view_menu.actions():
            if action.text() in self.plugins:
                # LOGGER.debug("Remove action <%s>", action.text())
                self.view_menu.removeAction(action)
                action.deleteLater()

        # Remove tool menu actions linked to the dialog plugins
        for action in self.tool_menu.actions():
            if action in self.dialog_plugins:
                # LOGGER.debug("Remove action <%s>", action.text())
                self.tool_menu.removeAction(action)
                action.deleteLater()

        # Purge widgets and related docks
        for plugin_obj in self.plugins.values():
            # LOGGER.debug("Remove plugin <%s>", plugin_obj)
            if plugin_obj.dock is not None:
                # Some plugins are not in docks (like central/footer tabs)
                self.removeDockWidget(plugin_obj.dock)
                plugin_obj.dock.close()
                plugin_obj.dock.deleteLater()

            plugin_obj.on_close()
            plugin_obj.deleteLater()

        # Clean registered plugins
        self.plugins = {}
        self.dialog_plugins = {}
        # Register new plugins
        self.register_plugins()
        self.open_database(self.conn)
        # Allow a user to save further modifications
        self.requested_reset_ui = False

    def copy_variants_to_clipboard(self):
        if "variant_view" in self.plugins:
            self.plugins["variant_view"].copy()

    def select_all_variants(self):
        """Select all elements in the current tab's view"""
        if "variant_view" in self.plugins:
            self.plugins["variant_view"].select_all()

    def closeEvent(self, event):
        """Save the current state of this mainwindow's toolbars and dockwidgets

        .. warning:: Make sure that the property objectName is unique for each
            QToolBar and QDockWidget added to the QMainWindow.

        .. note:: Reset windowState if asked.
        """
        self.write_settings()
        super().closeEvent(event)

    def write_settings(self):
        """Store the state of this mainwindow.

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

    # @Slot()
    # def on_query_model_changed(self):
    #     for name, _plugin in self.plugins.items():
    #         if _plugin.isVisible():
    #             _plugin.on_query_model_changed(self.query_model)

    # @Slot()
    # def on_variant_changed(self, variant):
    #     for name, _plugin in self.plugins.items():
    #         if _plugin.isVisible():
    #             _plugin.on_variant_changed(variant)


if __name__ == "__main__":
    app = QApplication(sys.argv)

    w = MainWindow()

    w.show()

    app.exec_()
