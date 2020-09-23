"""Handle and define plugins

Classes:

    - PluginWidget
    - PluginDialog
    - PluginSettingsWidget

Function to find and load plugins:
    - find_plugins

Plugin directory structure
--------------------------

Example:

    plugin_name
    ├── __init__.py
    ├── widgets.py
    └── dialogs.py

A plugin directory must be named in snake_case. It contains modules whose will
be described later and a __init__.py file which describes the plugin with the
following mandatory variables:

    .. code-block:: javascript

        __title__ = "PluginName"
        __description__ = "A plugin to cook variants"
        __author__ = "E. Micron"
        __version__ = "1.0.0"

Note: __title__ will be used on the GUI.

Plugin types
------------

Three kinds of plugins are supported, each one corresponds to a module in
a plugin directory.

    - Module named `widgets.py`:
        `widget` type: Parent class `PluginWidget`;
        Widget will be displayed on the main window according to the
        attribute `widget_location` of `PluginWidget`.
    - Module named `dialogs.py`:
        `dialog` type: Parent class `PluginDialog`;
        Dialog widget will be accessible from the tool menu of the UI.
    - Module named `settings.py`:
        `setting` type: Parent class `PluginSettingsWidget`;
        Widget will be accessible from the settings of the app.

That is, a plugin can support these 3 types simultaneously, but types must
be unique (i.e. no multiple widgets, or dialogs, or settings).


Module content
--------------

Instantiated classes of the modules will be those that inherit of the
expected parent class associated to their types (widget, dialog, setting).
In other words, each module **must** contains **one** class that inherits
from `PluginWidget` or `PluginDialog` or `PluginSettingsWidget`.

These classes **must** be named according to the name of the plugin directory
followed by the corresponding type, in the CamelCase convention.

Example:

    A plugin `word_set` could contain one module named `widgets.py`.
    This module contains almost one class named `WordSetWidget` that inherits
    from `PluginWidget`.

"""
# Standard import
import os
import importlib
import pkgutil

# Qt imports
from PySide2.QtWidgets import QWidget, QDialog

# Cutevariant import
from cutevariant.gui import settings

DOCK_LOCATION = 1
CENTRAL_LOCATION = 2
FOOTER_LOCATION = 3


def snake_to_camel(name: str) -> str:
    """Convert snake case to camel case

    Args:
        name (str): a snake string like : query_view

    Returns:
        str: a camel string like: QueryView
    """

    return "".join([i.capitalize() for i in name.split("_")])


class PluginWidget(QWidget):
    """Model class for all widget plugins

    .. note:: Please override the functions of this class as much as possible.

    Class attributes:
        - LOCATION: Location of the plugin in the interface (QMainWindow)
            Can be: DOCK_LOCATION, CENTRAL_LOCATION, FOOTER_LOCATION
        - ENABLE: If False, the plugin is disabled and will not be loaded;
            (used for development purpose).

    Attributes:
        - mainwindow: Parent widget
        - widget_location: Instance variable, equivalent to class variable LOCATION
    """

    LOCATION = DOCK_LOCATION
    ENABLE = False

    def __init__(self, parent=None):
        super().__init__(parent)
        self.mainwindow = None
        self.widget_location = DOCK_LOCATION

        self.refresh_groups = []  # TODO

    def on_register(self, mainwindow):
        """Called when the mainwindow is build

        You should setup the mainwindow with your plugin from here.

        Don't forget to assign mainwindow attribute with the given argument
        if you didn't do it in the constructor. It's your last chance!

        Args:
            mainwindow (QMainWindow): cutevariant Mainwindow
        """
        pass

    def on_open_project(self, conn):
        """This method is called when a project is opened

        You should use the sql connector if your plugin uses the SQL database.

        Args:
            conn (sqlite3.connection): A connection to the sqlite project
        """
        pass

    def on_close(self):
        """Called when the mainwindow is closed **or** when the plugin is reset.

        In order to have a clean reset, please add routines to delete all
        widgets added to the mainwindow (actions in toolbars, etc.).

        .. seealso:: :meth:`cutevariant/gui/mainwindow.MainWindow.reset_ui`
        """
        self.close()

    def on_refresh(self):
        """Called to refresh the GUI of the current plugin

        This is called by the mainwindow.controller::refresh methods
        """
        pass


class PluginDialog(QDialog):
    """Model class for all tool menu plugins

    These plugins are based on DialogBox; this means that they could be opened
    from the tools menu.
    """

    ENABLE = False

    def __init__(self, parent=None):
        super().__init__(parent)
        self.mainwindow = None


class PluginSettingsWidget(settings.GroupWidget):
    """Model class for settings plugins"""

    def __init__(self, parent=None):
        super().__init__(parent)

    def on_refresh(self):
        pass


################################################################################


def find_plugins(path=None):
    """Find and return plugin descriptions from a directory

    See Also: Docstring of this module. For structure of a plugin directory.

    TODO: Dialog pour metrics...

    Example of yielded dict:

        .. code-block:: javascript

            {
                'name': 'word_set',
                'title': 'WordSet',
                'description': 'A plugin to manage word set',
                'version': '1.0.0',
                'widget': <class 'widgets.WordSetWidget'>,
                'dialog': <class 'widgets.PluginDialog'>
            }

    Keyword Arguments:
        path [str] -- the folder path where plugin are

    Returns:
        [generator [Plugin]] -- A Plugin class ready to be instantiated
    """
    # if path is None, return internal plugin path
    if path is None:
        plugin_path = os.path.join(os.path.dirname(__file__), "plugins")
    else:
        plugin_path = path

    # Loop over package in plugins directory
    for package in pkgutil.iter_modules([plugin_path]):
        package_path = os.path.join(plugin_path, package.name)
        spec = importlib.util.spec_from_file_location(
            package.name, os.path.join(package_path, "__init__.py")
        )
        module = spec.loader.load_module()

        widget_class_name = snake_to_camel(package.name) + "Widget"
        settings_class_name = snake_to_camel(package.name) + "SettingsWidget"
        dialog_class_name = snake_to_camel(package.name)

        # Load __init__ file data of the module
        plugin_item = {
            "name": module.__name__,
            "title": module.__title__,
            "description": module.__description__,
            "version": module.__version__,
        }

        for sub_module_info in pkgutil.iter_modules([package_path]):

            if sub_module_info.name not in ("widgets", "settings", "dialogs"):
                continue

            sub_module_path = os.path.join(
                sub_module_info.module_finder.path, sub_module_info.name + ".py"
            )
            spec = importlib.util.spec_from_file_location(
                sub_module_info.name, sub_module_path
            )
            sub_module = spec.loader.load_module()

            if (
                widget_class_name in dir(sub_module)
                and sub_module_info.name == "widgets"
            ):
                Widget = getattr(sub_module, widget_class_name)
                if "PluginWidget" in str(Widget.__bases__):
                    plugin_item["widget"] = Widget

            if (
                settings_class_name in dir(sub_module)
                and sub_module_info.name == "settings"
            ):
                Widget = getattr(sub_module, settings_class_name)
                if "PluginSettingsWidget" in str(Widget.__bases__):
                    plugin_item["setting"] = Widget

            if (
                dialog_class_name in dir(sub_module)
                and sub_module_info.name == "dialogs"
            ):
                Widget = getattr(sub_module, dialog_class_name)
                if "PluginDialog" in str(Widget.__bases__):
                    plugin_item["dialog"] = Widget

        yield plugin_item
