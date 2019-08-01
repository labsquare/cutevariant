from cutevariant.gui import plugin

from PySide2.QtWidgets import *
import sys 
import sqlite3

from cutevariant.gui.plugins.filter import widget
from cutevariant import commons as cm

LOGGER = cm.logger()


class FilterPlugin(plugin.Plugin):
    def __init__(self, parent = None):
        super().__init__(parent) 
        self.view = widget.FilterWidget()
        self.view.model.filterChanged.connect(self.on_filter_changed)

    def get_widget(self):
        """Overload from Plugin
        
        Returns:
            QWidget
        """
        return self.view

    def on_open_project(self, conn):
        """Overload from Plugin
        
        Arguments:
            conn 
        """
        self.view.model.conn = conn 

    def on_filter_changed(self):
        """ methods called by self.view.model.filterchanged """ 

        self.mainwindow.query_widget.model.filter = self.view.model.to_dict()
        self.mainwindow.query_widget.model.load()

    def on_query_model_changed(self):
        self.view.model.load(self.mainwindow.query_widget.model.filter)


 


    



if __name__ == "__main__":
    
    app = QApplication(sys.argv)

    p = FilterPlugin()

    w = p.get_widget()

    w.show()


    app.exec_()