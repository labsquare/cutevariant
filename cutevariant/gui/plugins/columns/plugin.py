from cutevariant.gui import plugin

from PySide2.QtWidgets import *
import sys 
import sqlite3

from cutevariant.gui.plugins.columns import widget

class ColumnsPlugin(plugin.Plugin):
    def __init__(self, parent = None):
        super().__init__(parent) 

        self.view = widget.ColumnsWidget()
        self.view.changed.connect(self.on_column_changed) 


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
        self.view.conn = conn 

    def on_column_changed(self):
        self.mainwindow.query_widget.model.columns = self.view.columns
        self.mainwindow.query_widget.model.load()

    def on_query_model_changed(self):
        self.view.columns = self.mainwindow.query_widget.model.columns


    



if __name__ == "__main__":
    
    app = QApplication(sys.argv)

    p = ColumnsPlugin()

    w = p.get_widget()

    w.show()


    app.exec_()