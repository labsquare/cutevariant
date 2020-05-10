# Qt imports
from PySide2.QtWidgets import QWidget
from PySide2.QtCore import Signal


#  standard import
from glob import glob
import os
import importlib
import pkgutil

# cutevariant import 
from cutevariant.gui import settings

DOCK_LOCATION = 1 
CENTRAL_LOCATION = 2 
FOOTER_LOCATION = 3


def snake_to_camel(name:str) -> str:
    """Convert snake case to camel case
    
    Args:
        name (str): a snake string like : query_view
    
    Returns:
        str: a camel string like: QueryView
    """

    return "".join([i.capitalize() for i in name.split("_")])




class PluginWidget(QWidget):

    LOCATION = DOCK_LOCATION
    ENABLE = False

    def __init__(self, parent = None):
        super().__init__(parent)
        self.mainwindow = None
        self.widget_location = DOCK_LOCATION


    def on_register(self, mainwindow):
        """This method is called when the mainwindow is build 
        You should setup the mainwindow with your plugin from here.
        
        Args:
            mainwindow (MainWindow): cutevariant Mainwindow 
        """
        pass

    def on_open_project(self, conn):
        """This method is called when a project open
        
        Args:
            conn (sqlite3.connection): A connection to the sqlite project
        """
        pass

    def on_query_model_changed(self, model):
        """ DEPRECATED 
        """
        pass

    def on_variant_changed(self,variant):
        """This method is called when a variant is clicked. 
        The signal must be sended from mainwindow
        
        Args:
            variant (dict): contains data of a variant
        """
        pass

    def on_close(self):
        """This methods is called when the mainwindow close
        """
        pass


    def on_refresh(self):
        """ This methods is called to refresh the gui """
        pass 



class PluginSettingsWidget(settings.GroupWidget):
    def __init__(self, parent = None):
        super().__init__(parent)


def find_plugins(path=None):
    """find and returns plugin instance from a directory 
    
    Keyword Arguments:
        path [str] -- the folder path where plugin are 
        parent [type] -- the parent object of all instance. It must be the MainWindow
    
    Returns:
        [Plugin] -- An instance of Plugin class 
    """
    #  if path is None, return internal plugin path
    if path is None:
        plugin_path = os.path.join(os.path.dirname(__file__), "plugins")
    else:
        plugin_path = path

    # Loop over package in plugins directory
    plugins = []
    for package in pkgutil.iter_modules([plugin_path]):
        package_path = os.path.join(plugin_path, package.name)
        spec = importlib.util.spec_from_file_location(package.name, os.path.join(package_path, "__init__.py"))
        module = spec.loader.load_module()

        widget_class_name = snake_to_camel(package.name) + "Widget"
        settings_class_name = snake_to_camel(package.name)+ "SettingsWidget"

        item = {}
        item["name"] = module.__name__
        item["description"] = module.__description__
        item["version"] = module.__version__

        for sub_module_info in pkgutil.iter_modules([package_path]):
            if sub_module_info.name in ("widgets", "settings"):
                sub_module_path = os.path.join(sub_module_info.module_finder.path, sub_module_info.name +".py")
                spec = importlib.util.spec_from_file_location(sub_module_info.name,sub_module_path )
                sub_module = spec.loader.load_module()

                if widget_class_name in dir(sub_module) and sub_module_info.name == "widgets":
                    Widget = getattr(sub_module, widget_class_name)
                    if "PluginWidget" in str(Widget.__bases__):
                        item["widget"] = Widget

                if settings_class_name in dir(sub_module) and sub_module_info.name == "settings":
                    Widget = getattr(sub_module, settings_class_name)
                    if "PluginSettingsWidget" in str(Widget.__bases__):
                        item["setting"] = Widget
       
        
        yield item


