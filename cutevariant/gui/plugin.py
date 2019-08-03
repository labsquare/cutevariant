# Qt imports
from PySide2.QtWidgets import QWidget
from PySide2.QtCore import Signal

#  standard import
from glob import glob


class Plugin(object):
    """Base class for Plugin """

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
