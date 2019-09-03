# Qt imports
from PySide2.QtWidgets import QWidget
from PySide2.QtCore import Signal


#  standard import
from glob import glob
import os
import importlib


class Plugin(object):
    """Base class for Plugin """

    Name = "No Name"
    Description = ""

    def __init__(self, parent=None):
        super().__init__()
        self.mainwindow = parent
        self.dockable = True

    def on_query_model_changed(self):
        """ This method is called when QueryModel changed """
        pass

    def on_variant_clicked(self, variant):
        """ This method is called when a a variant is selected from the QueryModel """
        pass

    def on_register(self):
        """ This method is called when plugin has been registered to the mainwindow """
        pass

    def on_close(self):
        """ this method is called when plugin closed """
        pass

    def on_open_project(self, conn):
        """This method is called when a new project connection happen
        
        Arguments:
            conn sqlite3.connection 
        """
        pass

    def get_widget(self) -> QWidget:
        """Return the plugin  widget 
        
        Returns:
            QWidget 
        """
        return None

    def get_settings_widget(self) -> QWidget:
        """Return the plugin settings widget
        
        Returns:
            QWidget 
        """
        return None


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

    #  get all packages from the path
    # TODO: check if they are packages
    paths = [f.path for f in os.scandir(plugin_path) if f.is_dir()]

    #  Loop over packages and load Plugin dynamically
    for path in paths:
        #  module name example : test
        module_name = os.path.basename(path)
        #  class name example : TestPlugin
        class_name = module_name.capitalize() + "Plugin"

        spec = importlib.util.spec_from_file_location(
            module_name, path + "/plugin.py"
        )
        if spec:
            # load the module
            module = spec.loader.load_module()
            # load the class
            Plugin = getattr(module, class_name)
            yield Plugin