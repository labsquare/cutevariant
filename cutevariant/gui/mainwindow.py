"""Main window of Cutevariant"""
# Standard imports
import os
import sys
import sqlite3
import json
import typing
from pkg_resources import parse_version
from functools import partial
from logging import DEBUG

# Qt imports
from PySide2.QtCore import Qt, QSettings, QByteArray, QDir, QUrl, Signal, QSize
from PySide2.QtWidgets import *
from PySide2.QtGui import QIcon, QKeySequence, QDesktopServices


# Custom imports
from cutevariant import LOGGER
from cutevariant.core import get_sql_connection, get_metadatas, command
from cutevariant.core import sql
from cutevariant.core.sql import get_database_file_name
from cutevariant.core.writer import CsvWriter, PedWriter
from cutevariant.gui import FIcon
from cutevariant.gui.wizards import ProjectWizard
from cutevariant.gui.settings import SettingsDialog
from cutevariant.gui.widgets.aboutcutevariant import AboutCutevariant
from cutevariant import commons as cm
from cutevariant.commons import (
    MAX_RECENT_PROJECTS,
    DIR_ICONS,
    MIN_AUTHORIZED_DB_VERSION,
)

from cutevariant.gui.export import ExportDialogFactory, ExportDialog

# Import plugins
from cutevariant.gui import plugin, plugin_form

from cutevariant import LOGGER

import copy


class StateData:
    """A dictonnary like object which monitor which key changed

    This is used to store application data and refresh plugins if it is required

    """

    def __init__(self):
        self._changed = set()
        self.reset()

    def __setitem__(self, key, value):

        if key in self._data:
            if self._data[key] == value:
                return

        self._changed.add(key)
        self._data[key] = copy.deepcopy(value)

    def __getitem__(self, key):
        if key in self._data:
            return self._data[key]
        return None

    def clear_changed(self):
        self._changed.clear()

    @property
    def changed(self):
        return self._changed

    def reset(self):
        self._data = {
            "fields": ["favorite", "classification", "chr", "pos", "ref", "alt"],
            "source": "variants",
            "filters": {},
        }


class MainWindow(QMainWindow):
    """Cutevariant mainwindow

    The mainwindow is build by with plugins loaded from /cutevariant/gui/plugins.
    It also plays the role of a mediator between plugins where data are read and write from the state_data attributes.

    Attributes:
        conn (sqlite.Connection): the sqlite databases
        plugins : a dictionnary of plugins with plugin name as key

    """

    def __init__(self, parent=None):

        super().__init__(parent)

        ## ===== CLASS ATTRIBUTES =====
        self.conn = None
        # Plugins
        self.plugins = {}  # dict of plugins with plugin name as key
        self.dialog_plugins = {}  # dict of dialog plugins

        # Settings
        self.app_settings = QSettings()

        # State variable of application changed by plugins
        self._state_data = StateData()

        ## ===== GUI Setup =====
        self.setWindowTitle("Cutevariant")
        self.setWindowIcon(QIcon(DIR_ICONS + "app.png"))
        self.setWindowFlags(Qt.WindowContextHelpButtonHint | self.windowFlags())

        # Setup ToolBar
        self.toolbar = self.addToolBar("maintoolbar")
        self.toolbar.setObjectName("maintoolbar")  # For window saveState
        self.toolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)

        # Setup menu bar
        self.setup_actions()

        # Setup Central widget
        self.central_tab = QTabWidget()
        self.footer_tab = QTabWidget()
        self.vsplit = QSplitter(Qt.Vertical)
        self.vsplit.addWidget(self.central_tab)
        self.vsplit.addWidget(self.footer_tab)
        self.vsplit.setHandleWidth(5)
        self.setCentralWidget(self.vsplit)
        self.setTabPosition(Qt.AllDockWidgetAreas, QTabWidget.North)
        # registers plugins
        self.register_plugins()

        # Setup status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # Window geometry
        self.resize(600, 400)
        self.setGeometry(
            QApplication.instance().desktop().rect().adjusted(100, 100, -100, -100)
        )

        # If True, the GUI settings are deleted when the app is closed
        self.requested_reset_ui = False
        # Restores the state of this mainwindow's toolbars and dockwidgets
        self.read_settings()

        # Auto open recent projects
        recent = self.get_recent_projects()
        if recent and os.path.isfile(recent[0]):
            self.open(recent[0])

    def set_state_data(self, key: str, value: typing.Any):
        """set state data value from key

        This method must be called by plugins to change state_data.
        Do not use the  protected attribut (`self._state_data`) because the following method store and detect changes

        Args:
            key (str): Name of the state variable ( fields, source, filters )
            value (Any): a value
        """
        self._state_data[key] = value

    def get_state_data(self, key: str) -> typing.Any:
        """Get state data value from from key

        This method must be called by plugins to reads state_data

        Args:
            key (str): Name of the state variable

        Returns:
            typing.Any: Return a value
        """

        return self._state_data[key]

    def add_panel(self, widget, area=Qt.LeftDockWidgetArea):
        """Add the given widget to a new QDockWidget.

        It the most of the case, it is a PlufinWidget with PluginWidget.LOCATION equal to DOCK_LOCATION

        Note:
            Adding panel will append a hide/show action in the view menu

        Args:                LOGGER.debug("Connected variant view signals to mainwindow")

            widget (QWidget): a standard QWidget like a PluginWidget
            area: Area location. Defaults to Qt.LeftDockWidgetArea.
        """
        dock = QDockWidget()
        dock.setWindowTitle(widget.windowTitle())
        dock.setWidget(widget)
        dock.setStyleSheet("QDockWidget { font: bold }")
        # Keep the attached dock to allow further clean deletion
        widget.dock = dock
        # Set the objectName for a correct restoration after saveState
        dock.setObjectName(str(widget.__class__))

        self.addDockWidget(area, dock)
        action = dock.toggleViewAction()
        action.setIcon(widget.windowIcon())
        action.setText(widget.windowTitle())
        self.view_menu.addAction(action)

        # self.toolbar.addAction(action)

    def register_plugins(self):
        """Load all plugins to the window

        See self.register_plugin

        """
        LOGGER.info("Registering plugins...")
        # Get classes of plugins
        for extension in plugin.find_plugins():
            self.register_plugin(extension)

    def register_plugin(self, extension):
        """Load a plugin to the Mainwindow

        There are Two kinds of plugins which can be registered:
        - PluginWidget: Added to the mainwindow as QDockWidget or TabWidget
        - PluginDialog: DialogBox accessible from the tool menu.

        Note:
            PluginSettingsWidget is handled separately in`cutevariant.gui.settings.load_plugins`

        Args:
            extension (dict): Extension dict returned by `cutevariant.gui.plugin.find_plugins`
        """

        name = extension["name"]
        title = extension["title"]
        displayed_title = title

        if "widget" in extension and extension["widget"].ENABLE:
            # New GUI widget
            plugin_widget_class = extension["widget"]

            # Setup new widget
            widget = plugin_widget_class(parent=self)
            widget.setDisabled(True)

            if not widget.objectName():
                LOGGER.debug(
                    "widget '%s' has no objectName attribute; "
                    "=> fallback to extension name",
                    displayed_title,
                )
                widget.setObjectName(name)

            # Set title
            widget.setWindowTitle(displayed_title)

            # WhatsThis content
            long_description = extension.get("long_description")
            if not long_description:
                long_description = extension.get("description")
            widget.setWhatsThis(long_description)
            # Register (launch first init on some of them)
            widget.mainwindow = self
            widget.on_register(self)
            # if self.conn:
            #     # If register occurs after a project is loaded we must set its
            #     # connection attribute
            #     widget.on_open_project(self.conn)

            # Init mainwindow via the constructor or on_register

            # Add new plugin to plugins already registered
            self.plugins[name] = widget

            # Set position on the GUI
            if plugin_widget_class.LOCATION == plugin.DOCK_LOCATION:
                self.add_panel(widget)

            if plugin_widget_class.LOCATION == plugin.CENTRAL_LOCATION:
                self.central_tab.addTab(widget, widget.windowTitle())

            if plugin_widget_class.LOCATION == plugin.FOOTER_LOCATION:
                self.footer_tab.addTab(widget, widget.windowTitle())

        if "dialog" in extension and extension["dialog"].ENABLE:
            # New tool menu entry
            plugin_dialog_class = extension["dialog"]

            # Add plugin to Tools menu
            dialog_action = self.tool_menu.addAction(displayed_title + "...")
            self.dialog_plugins[dialog_action] = plugin_dialog_class
            dialog_action.triggered.connect(self.show_dialog)

    def refresh_plugins(self, sender: plugin.PluginWidget = None):
        """Refresh all widget plugins

        It doesn't refresh a plugin if :

        - the plugin is the sender
        - the plugin is not visible
        - the plugin specified a class variable REFRESH_STATE_DATA = ["fields"]

        Args:
            sender (PluginWidget): from a plugin, you can pass "self" as argument
        """

        plugin_to_refresh = []
        for plugin_obj in self.plugins.values():
            need_refresh = (
                plugin_obj is not sender
                and (plugin_obj.isVisible() or not plugin_obj.REFRESH_ONLY_VISIBLE)
                and (set(plugin_obj.REFRESH_STATE_DATA) & self._state_data.changed)
            )

            if need_refresh:
                try:
                    plugin_to_refresh.append(plugin_obj)
                    # plugin_obj.on_refresh()
                    LOGGER.debug(f"refresh {plugin_obj.__class__}")

                except Exception as e:
                    LOGGER.exception(e)

        # Clear state_changed set
        self._state_data.clear_changed()
        for plugin in plugin_to_refresh:
            plugin.on_refresh()

    def refresh_plugin(self, plugin_name: str):
        """Refresh a widget plugin identified by plugin_name

        It doesn't refresh the sender plugin

        Args:
            plugin_name (str): Name of the plugin to be refreshed
        """
        if plugin_name in self.plugins:
            plugin_obj = self.plugins[plugin_name]
            plugin_obj.on_refresh()

    def setup_actions(self):
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
            self.tr("&Open project..."),
            self.open_project,
            QKeySequence.Open,
        )

        self.toolbar.addAction(self.new_project_action)
        self.toolbar.addAction(self.open_project_action)
        self.toolbar.addAction(
            FIcon(0xF02D7), self.tr("Help"), QWhatsThis.enterWhatsThisMode
        )
        self.toolbar.addSeparator()

        ### Recent projects
        self.recent_files_menu = self.file_menu.addMenu(self.tr("Open recent"))

        self.setup_recent_menu()

        self.file_menu.addAction(QIcon(), self.tr("Export..."), self.on_export_pressed)

        self.export_menu = self.file_menu.addMenu(self.tr("Export as"))

        for export_format_name in ExportDialogFactory.get_supported_formats():

            action = self.export_menu.addAction(
                self.tr(f"Export as {export_format_name}..."), self.on_export_pressed
            )

            # Since there are several actions connected to the same slot, we need to pass the format to the receiver
            action.setData(export_format_name)

        # self.export_ped_action = self.file_menu.addAction(
        #     self.tr("Export pedigree PED/PLINK"), self.export_ped
        # )

        self.file_menu.addSeparator()

        self.file_menu.addAction(
            FIcon(0xF0193), self.tr("Save session ..."), self.save_session
        )
        self.file_menu.addAction(
            FIcon(0xF0770), self.tr("Restore session ..."), self.load_session
        )

        self.file_menu.addSeparator()
        ### Misc
        self.file_menu.addAction(
            FIcon(0xF0493), self.tr("Settings..."), self.show_settings
        )
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.tr("&Quit"), self.close, QKeySequence.Quit)

        ## Edit
        # TODO: if variant_view plugin is not loaded, disable this menu entries...
        self.edit_menu = self.menuBar().addMenu(self.tr("&Edit"))
        self.edit_menu.addAction(
            FIcon(0xF018F),
            self.tr("&Copy selected variants"),
            self.copy_variants_to_clipboard,
            "ctrl+shift+c",
        )
        self.edit_menu.addSeparator()
        self.edit_menu.addAction(
            FIcon(0xF0486),
            self.tr("&Select all variants"),
            self.select_all_variants,
            QKeySequence.SelectAll,
        )

        ## View
        self.view_menu = self.menuBar().addMenu(self.tr("&View"))
        self.view_menu.addAction(self.tr("Reset widgets positions"), self.reset_ui)
        # Set toggle footer visibility action
        show_action = self.view_menu.addAction(
            FIcon(0xF018D), self.tr("Show VQL editor")
        )
        show_action.setCheckable(True)
        self.toolbar.addAction(show_action)
        show_action.setChecked(True)
        show_action.toggled.connect(self.toggle_footer_visibility)

        fullscreen_action = self.view_menu.addAction(
            self.tr("Enter Full Screen"),
        )

        fullscreen_action.setShortcut(QKeySequence.FullScreen)
        fullscreen_action.setCheckable(True)
        fullscreen_action.toggled.connect(
            lambda x: self.showFullScreen() if x else self.showNormal()
        )

        self.view_menu.addSeparator()

        ## Tools
        self.tool_menu = self.menuBar().addMenu(self.tr("&Tools"))

        ## Help
        self.help_menu = self.menuBar().addMenu(self.tr("Help"))

        self.help_menu.addAction(
            FIcon(0xF02D6),
            self.tr("What's this"),
            QWhatsThis.enterWhatsThisMode,
            QKeySequence.WhatsThis,
        )
        self.help_menu.addAction(
            FIcon(0xF059F),
            self.tr("Documentation..."),
            partial(QDesktopServices.openUrl, QUrl(cm.WIKI_URL, QUrl.TolerantMode)),
        )
        self.help_menu.addAction(
            FIcon(0xF0A30),
            self.tr("Report a bug..."),
            partial(
                QDesktopServices.openUrl, QUrl(cm.REPORT_BUG_URL, QUrl.TolerantMode)
            ),
        )

        self.help_menu.addSeparator()
        # Setup developers menu
        self.developers_menu = QMenu(self.tr("Developers..."))
        self.setup_developers_menu()
        self.help_menu.addMenu(self.developers_menu)

        self.help_menu.addAction(
            self.tr("About Qt..."), QApplication.instance().aboutQt
        )
        self.help_menu.addAction(
            QIcon(DIR_ICONS + "app.png"),
            self.tr("About Cutevariant..."),
            self.about_cutevariant,
        )

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
        self.app_settings.setValue("last_directory", os.path.dirname(filepath))

        # Create connection
        self.conn = get_sql_connection(filepath)

        try:
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
                    self.tr("File: {} is too old; please create a new project.").format(
                        filepath
                    ),
                )
                return

            self.open_database(self.conn)
            self.save_recent_project(filepath)

        except sqlite3.OperationalError as e:
            LOGGER.exception(e)
            QMessageBox.critical(
                self,
                self.tr("Error while opening project"),
                self.tr("File: {}\nThe following exception occurred:\n{}").format(
                    filepath, e
                ),
            )
            return

        # Show the project name in title and in status bar
        self.setWindowTitle("Cutevariant - %s" % os.path.basename(filepath))
        self.status_bar.showMessage(self.tr("{} opened").format(filepath))

    def open_database(self, conn):
        """Open the project file and populate widgets

        Args:
            conn (sqlite3.Connection): Sqlite3 Connection
        """
        self.conn = conn

        self._state_data.reset()

        # Clear memoization cache for count_cmd
        sql.clear_lru_cache()
        # Clear State variable of application
        # store fields, source, filters, group_by, having data

        # Load previous window state for this project (file_path being the key for the settings)
        file_path = get_database_file_name(conn)

        # self.state = self.app_settings.value(f"{file_path}/last_state", State())

        for plugin_obj in self.plugins.values():
            plugin_obj.on_open_project(self.conn)
            plugin_obj.setEnabled(True)

    def save_recent_project(self, path):
        """Save current project into QSettings

        Args:
            path (str): path of project
        """
        paths = self.get_recent_projects()
        if path in paths:
            paths.remove(path)
        paths.insert(0, path)

        self.app_settings.setValue("recent_projects", paths[:MAX_RECENT_PROJECTS])

    def get_recent_projects(self):
        """Return the list of recent projects stored in settings

        Returns:
            list: Recent project paths
        """
        # Reload last projects opened
        recent_projects = self.app_settings.value("recent_projects", list())

        # Check if recent_projects is a list() (as expected)
        if isinstance(recent_projects, str):
            recent_projects = [recent_projects]

        # Return only existing project files
        return [p for p in recent_projects if os.path.exists(p)]

    def clear_recent_projects(self):
        """Slot to clear the list of recent projects"""
        self.app_settings.remove("recent_projects")
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
        last_directory = self.app_settings.value("last_directory", QDir.homePath())

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

    def export_as_csv(self):
        """Export variants into CSV file"""
        # Reload last directory used
        last_directory = self.app_settings.value("last_directory", QDir.homePath())

        filepath, _ = QFileDialog.getSaveFileName(
            self, self.tr("Save project"), last_directory, self.tr("(*.csv)")
        )

        if filepath:
            with open(filepath, "w") as file:
                writer = CsvWriter(file)
                writer.save(self.conn)

    def export_ped(self):
        """Export samples into PED/PLINK file"""
        # Reload last directory used
        last_directory = self.app_settings.value("last_directory", QDir.homePath())

        # noinspection PyCallByClass
        filepath, _ = QFileDialog.getSaveFileName(
            self, self.tr("Save project"), last_directory, "(*.tfam)"
        )

        if filepath:
            filepath = filepath if filepath.endswith(".tfam") else filepath + ".tfam"

            with open(filepath, "w") as file:
                writer = PedWriter(file)
                writer.save(self.conn)

    def show_settings(self):
        """Slot to show settings window"""
        widget = SettingsDialog(self)

        if widget.exec_():
            self.reload()

    def reload(self):
        self.open_database(self.conn)

    def show_dialog(self):
        """Show Plugin dialog box after a click on the tool menu"""
        action = self.sender()
        if action in self.dialog_plugins:
            # Get class object and instantiate it
            dialog_class = self.dialog_plugins[action]
            # Send SQL connection
            dialog = dialog_class(conn=self.conn)
            dialog.mainwindow = self
            dialog.exec_()

    def about_cutevariant(self):
        """Slot to show about window"""
        dialog_window = AboutCutevariant(self)
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
        for index in range(self.central_tab.count()):
            self.central_tab.removeTab(index)

        for index in range(self.footer_tab.count()):
            self.footer_tab.removeTab(index)

        # Remove tool menu actions linked to the dialog plugins
        for action in self.dialog_plugins:
            # LOGGER.debug("Remove action <%s>", action.text())
            self.tool_menu.removeAction(action)
            action.deleteLater()

        # Purge widgets (central/footer and others) and related docks
        for plugin_obj in self.plugins.values():
            # LOGGER.debug("Remove plugin <%s>", plugin_obj)
            self.removeDockWidget(plugin_obj.dock)
            plugin_obj.on_close()

        # Clean registered plugins
        self.plugins = {}
        self.dialog_plugins = {}
        # Register new plugins
        self.register_plugins()
        # We reload everything, but do not forget the project's file name !
        self.open_database(self.conn)
        # Allow a user to save further modifications
        self.requested_reset_ui = False

    def deregister_plugin(self, extension):
        """Delete plugin from the UI; Called from app settings when a plugin is disabled.

        - dialogs plugins: Remove action from tool menu
        - widgets plugins: Delete widget and its dock if available via its
            on_close() method.

        Args:
            extension (dict): Extension dict. See :meth:`cutevariant.gui.plugin.find_plugins`
        """
        name = extension["name"]
        title = extension["title"]
        displayed_title = name if LOGGER.getEffectiveLevel() == DEBUG else title

        # Remove tool menu actions linked to the dialog plugins
        for action in self.dialog_plugins:
            if action.text() == displayed_title:
                # LOGGER.debug("Remove action <%s>", action.text())
                self.tool_menu.removeAction(action)
                action.deleteLater()
                del self.dialog_plugins[action]
                break

        # Purge widgets and related docks
        if name in self.plugins:
            plugin_obj = self.plugins[name]
            # LOGGER.debug("Remove plugin <%s>", plugin_obj)
            self.removeDockWidget(plugin_obj.dock)
            plugin_obj.on_close()
            del self.plugins[name]

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

        # Don't forget to tell all the plugins that the window is being closed
        for plugin_obj in self.plugins.values():
            plugin_obj.on_close()
        super().closeEvent(event)

    def save_session(self):
        """save plugin state into a json file"""

        filename, _ = QFileDialog.getSaveFileName(
            self,
            self.tr("Save the session"),
            QDir.home().path(),
            "Session file (*.session.json)",
        )

        if os.path.exists(filename):
            ret = QMessageBox.warning(
                self,
                "file already exists",
                "Overwrite?",
                QMessageBox.Yes | QMessageBox.No,
            )

            if ret == QMessageBox.No:
                return

        if not filename.endswith(".session.json"):
            filename = filename + ".session.json"

        #  write sessions
        session = {}
        for name, plugin in self.plugins.items():
            session[name] = plugin.to_json()

        #  write file
        with open(filename, "w") as file:
            json.dump(session, file)

    def load_session(self):
        filename, _ = QFileDialog.getOpenFileName(
            self,
            self.tr("Save the session"),
            QDir.home().path(),
            "Session file (*.session.json)",
        )

        if not os.path.exists(filename):
            return

        # read sessions
        with open(filename) as file:
            state = json.load(file)

        #  set plugins
        for name, plugin in self.plugins.items():
            if name in state:
                plugin.from_json(state[name])

    def write_settings(self):
        """Store the state of this mainwindow.

        .. note:: This methods is called by closeEvent
        """
        if self.requested_reset_ui:
            # Delete window state setting
            self.app_settings.remove("windowState")
        else:
            self.app_settings.setValue("geometry", self.saveGeometry())
            #  TODO: handle UI changes by passing UI_VERSION to saveState()
            self.app_settings.setValue("windowState", self.saveState())

    def read_settings(self):
        """Restore the state of this mainwindow's toolbars and dockwidgets

        .. note:: If windowState is not stored, current state is written.
        """
        # Init reset ui boolean
        self.requested_reset_ui = False

        self.restoreGeometry(QByteArray(self.app_settings.value("geometry")))
        #  TODO: handle UI changes by passing UI_VERSION to saveState()
        window_state = self.app_settings.value("windowState")
        if window_state:
            self.restoreState(QByteArray(window_state))
        else:
            # Setting has been deleted: set the current default state
            #  TODO: handle UI changes by passing UI_VERSION to saveState()
            self.app_settings.setValue("windowState", self.saveState())

    def toggle_footer_visibility(self, visibility):
        """Toggle visibility of the bottom toolbar and all its plugins"""
        # self.footer_tab.setVisible(visibility)
        if visibility:
            self.vsplit.setSizes([100, 0])
        else:
            self.vsplit.setSizes([200, 100])

    def on_export_pressed(self):
        """
        Slot called by any export action.
        Use QAction.setData() on the sender to set format name.
        Otherwise, this slot will guess the format based on the save file dialog
        """

        if not self.conn:
            QMessageBox.information(
                self,
                self.tr("Info"),
                self.tr("No project opened, nothing to export.\nAborting."),
            )
            return

        settings = QSettings()
        default_save_dir = settings.value("last_save_file_dir", QDir.homePath())

        # Supported export extensions to filter names in the save file dialog (all of them by default)

        factory = ExportDialogFactory()

        exts = factory.get_supported_formats()

        format_name = self.sender().data()

        # Narrow down available extensions based on the action that was triggered
        if format_name:
            exts = [format_name]

        filters_and_exts = {
            f"{ext.upper()} file (*.{ext})": ext for ext in exts
        }  # Hack to get only ext out of savefiledialog result's second element (associates the filter's message with the extension name)

        file_name, chosen_ext = QFileDialog.getSaveFileName(
            self,
            self.tr("Please chose a filename you'd like to save the database to"),
            default_save_dir,
            ";;".join(filters_and_exts.keys()),
        )

        if not file_name:
            return

        settings.setValue("last_save_file_dir", os.path.dirname(file_name))

        chosen_ext = filters_and_exts[
            chosen_ext
        ]  # Hacky, extracts extension from second element from getSaveFileName result

        # Automatic extension of file_name
        file_name = (
            file_name if file_name.endswith(chosen_ext) else f"{file_name}.{chosen_ext}"
        )

        export_dialog: ExportDialog = ExportDialogFactory.create_dialog(
            self.conn,
            chosen_ext,
            file_name,
            fields=self.get_state_data("fields"),
            source=self.get_state_data("source"),
            filters=self.get_state_data("filters"),
        )

        # # TODO : refactor self.state
        # export_dialog.state = {
        # "fields" : self.state.fields,
        # "source": self.state.source,
        # "filters": self.state.filters,
        # }

        success = export_dialog.exec_()
        if success == QDialog.Accepted:
            QMessageBox.information(
                self,
                self.tr("Success!"),
                self.tr(f"Successfully saved {os.path.basename(file_name)}"),
            )
        else:
            QMessageBox.critical(
                self,
                self.tr("Error!"),
                self.tr(f"Cannot save file to {os.path.basename(file_name)}"),
            )

    def setup_developers_menu(self):
        self.developers_menu.setIcon(FIcon(0xF1064))
        self.create_plugin_action: QAction = self.developers_menu.addAction(
            self.tr("Create new plugin")
        )
        self.create_plugin_action.setIcon(FIcon(0xF14D0))
        # The resulting dialog is created and generates the plugin
        self.create_plugin_action.triggered.connect(plugin_form.create_dialog_plugin)

        return self.developers_menu

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
