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

Note:
    - `__title__` will be used on the GUI for the name of the plugin.
    - `__long_description__` can be used to provide high quality helper text via
        tooltip or What's This functionality (question mark button on top of all
        windows). It can be written in html.
        If it is not specified, the variable `__description__` will be used instead.

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

These classes **must** be named in accordance to the name of the plugin directory
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
from PySide2.QtCore import QSettings

# Cutevariant import
from cutevariant.gui import settings
import cutevariant.commons as cm

LOGGER = cm.logger()

DOCK_LOCATION = 1
CENTRAL_LOCATION = 2
FOOTER_LOCATION = 3


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
        - conn (sqlite3.connection): A connection to the sqlite project
        - dock (None, optional): Keep the attached dock to allow further clean
            deletion.
    """

    LOCATION = DOCK_LOCATION
    ENABLE = False

    def __init__(self, parent=None):
        """Set parent window (mainwindow) to QWidget and to mainwindow attribute

        Keys:
            parent (QMainWindow): Mainwindow of Cutevariant, passed during
                plugin initialization.
        """
        super().__init__(parent)
        self.mainwindow = parent
        self.widget_location = DOCK_LOCATION
        self.conn = None
        self.dock = None

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

        Warnings:
            This routine **IS** important; if you override it, please don't forget
            to call `super().on_close()` at the end!

        .. seealso:: :meth:`cutevariant/gui/mainwindow.MainWindow.reset_ui`
        """
        self.close()
        self.deleteLater()
        LOGGER.debug("delete plugin... %s", self)
        if self.dock is not None:
            LOGGER.debug("delete its dock...")
            self.dock.close()
            self.dock.deleteLater()

    def on_refresh(self):
        """Called to refresh the GUI of the current plugin

        This is called by the mainwindow.controller::refresh methods
        """
        pass

    def showEvent(self, event):
        """Event called when a plugin is shown on the UI

        This is used to sync a plugin with the UI after it has been hidden.

        Note:
            Is also shown at the initialization => Test the SQL connection to
            avoid surprises due to an early call of `on_refresh`.

        Args:
            event(PySide2.QtGui.QShowEvent):
        """
        LOGGER.debug("Show event %s", self)
        if self.conn:
            self.on_refresh()


class PluginDialog(QDialog):
    """Model class for all tool menu plugins

    These plugins are based on DialogBox; this means that they could be opened
    from the tools menu.
    """

    ENABLE = False

    def __init__(self, parent=None):
        """
        Keys:
            parent (QMainWindow): cutevariant Mainwindow
        """
        super().__init__(parent)
        self.conn = None


class PluginSettingsWidget(settings.GroupWidget):
    """Model class for settings plugins"""

    ENABLE = False

    def __init__(self, parent=None):
        """
        Keys:
            parent (QMainWindow): cutevariant window (mainly SettingsWidget)
        """
        super().__init__(parent)

    def on_refresh(self):
        """Called to refresh the GUI of the current plugin

        This is called by the mainwindow.controller::refresh methods
        """
        pass


################################################################################

def snake_to_camel(name: str) -> str:
    """Convert snake_case name to CamelCase name

    Args:
        name (str): a snake string like : query_view

    Returns:
        str: a camel string like: QueryView
    """
    return "".join([i.capitalize() for i in name.split("_")])


def find_plugins(path=None):
    """Find and return plugin descriptions from a directory

    See Also: Docstring of this module. For structure of a plugin directory.

    Example of yielded dict:

        .. code-block:: javascript

            {
                'name': 'word_set',
                'title': 'WordSet',
                'description': 'A plugin to manage word set',
                'long_description': 'Long description used with WhatsThis help',
                'version': '1.0.0',
                'widget': <class 'widgets.WordSetWidget'>,
                'dialog': <class 'widgets.PluginDialog'>
            }

    Keyword Arguments:
        path(str): Folder path where plugin are

    Returns:
        (generator[dict]): A dict with classes ready to be instantiated
    """
    # if path is None, return internal plugin path
    if path is None:
        plugin_path = os.path.join(os.path.dirname(__file__), "plugins")
    else:
        plugin_path = path

    # Loop over packages in plugins directory
    for package in pkgutil.iter_modules([plugin_path]):
        package_path = os.path.join(plugin_path, package.name)
        LOGGER.debug("Loading plugin at <%s>", package_path)

        spec = importlib.util.spec_from_file_location(
            package.name, os.path.join(package_path, "__init__.py")
        )

        # TODO: maybe could use __title__ to build class names...
        widget_class_name = snake_to_camel(package.name) + "Widget"
        settings_class_name = snake_to_camel(package.name) + "SettingsWidget"
        dialog_class_name = snake_to_camel(package.name) + "Dialog"

        # Load __init__ file data of the module
        # We expect to load a plugin per module found in a plugin directory
        # This is the base dict of the item yielded from this function
        module = spec.loader.load_module()
        plugin_item = {
            "name": module.__name__,
            "title": module.__title__,
            "description": module.__description__,
            "long_description": module.__long_description__,
            "version": module.__version__,
        }

        authorized_module_classes = {
            "widgets": widget_class_name,
            "settings": settings_class_name,
            "dialogs": dialog_class_name,
        }

        authorized_base_clases = {
            "widgets": PluginWidget,
            "settings": PluginSettingsWidget,
            "dialogs": PluginDialog,
        }

        # Loop over modules in each plugin
        for sub_module_info in pkgutil.iter_modules([package_path]):
            LOGGER.debug("Loading module <%s>", sub_module_info)
            sub_module_type = sub_module_info.name

            # Filter module filenames
            if sub_module_type not in authorized_module_classes:
                continue

            # Dynamically load module
            sub_module_path = os.path.join(
                sub_module_info.module_finder.path, sub_module_type + ".py"
            )
            spec = importlib.util.spec_from_file_location(
                sub_module_type, sub_module_path
            )
            sub_module = spec.loader.load_module()

            # Filter not wanted classes (search main classes of the module)

            # Classes that don't have the module name in their name
            class_name = authorized_module_classes[sub_module_type]
            if class_name not in dir(sub_module):
                LOGGER.error(
                    "Plugin <%s.%s>, class <%s> not found!",
                    module.__name__, sub_module_type, class_name
                )
                continue

            class_item = getattr(sub_module, class_name)
            # # Purge disabled plugins
            # if not class_item.ENABLE:
            #     LOGGER.debug(
            #         "Plugin <%s.%s> disabled",
            #         module.__name__,
            #         sub_module_type
            #     )
            #     continue

            # Classes that don't inherit of the expected Plugin class
            # See cutevariant/gui/plugin.py
            if authorized_base_clases[sub_module_type] not in class_item.__bases__:
                LOGGER.error(
                    "Plugin <%s.%s>, parent class <%s> not found!",
                    module.__name__,
                    sub_module_type,
                    authorized_base_clases[sub_module_type].__name__
                )
                continue

            # Remove the "s" from module name...
            plugin_item[sub_module_type[:-1]] = class_item

            # Fix plugin status by user decision via app settings
            if not class_item.ENABLE:
                class_item.ENABLE = QSettings().value(
                    f"plugins/{plugin_item['name']}/status"
                ) == "true"

        yield plugin_item
