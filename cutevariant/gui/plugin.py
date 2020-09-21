# Qt imports
from PySide2.QtWidgets import QWidget, QDialog

# standard import
import os
import importlib
import pkgutil

# cutevariant import
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
        Don't forget to assign mainwindow attribute with the given argument.

        Args:
            mainwindow (MainWindow): cutevariant Mainwindow
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
        """Called when the mainwindow is closed"""
        pass

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
    """Find and return plugin classes from a directory

    Three kinds of plugins can be returned:

        - widget
        - dialog
        - setting

    Example:

        .. code-block:: javascript

            {
                'name': 'word_set',
                'title': 'WordSet',
                'description': ' A plugin to manage word set',
                'version': '1.0.0',
                'widget': <class 'widgets.WordSetWidget'>
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
