# Qt imports
from PySide2.QtWidgets import QWidget
from PySide2.QtCore import Signal


#  standard import
from glob import glob
import os
import importlib
import pkgutil

DOCK_LOCATION = 1 
CENTRAL_LOCATION = 2 
FOOTER_LOCATION = 3


class PluginWidget(QWidget):

    def __init__(self, parent = None):
        super().__init__(parent)
        self.mainwindow = None
        self.widget_location = DOCK_LOCATION

    def on_register(self):
        """This method is called when the plugin is register 
        """
        pass

    def on_setup_ui(self, mainwindow):
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
        """This method is called when the variant model changed 
        
        Args:
            model (QueryModel): QueryModel
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


#         return None


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

    plugin_item = {}

    # Loop over package in plugins directory
    for package in pkgutil.iter_modules([plugin_path]):
        
        widget_path = os.path.join(package.module_finder.path, package.name, "widgets.py")
        setting_path = None #TODO 
        spec = importlib.util.spec_from_file_location("widgets", widget_path)

        if spec:
            module = spec.loader.load_module()
            # capitalize only the first letter 
            class_name = package.name[0].upper() + package.name[1:] + "Widget"

            if class_name in dir(module):
                plugin_item["widget"] = getattr(module, class_name)
                yield plugin_item
            