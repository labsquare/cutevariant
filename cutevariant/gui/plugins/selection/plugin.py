from cutevariant.gui import plugin

from PySide2.QtWidgets import *
import sys 
import sqlite3

from cutevariant.gui.plugins.selection import widget

class SelectionPlugin(plugin.Plugin):
    def __init__(self, parent = None):
        super().__init__(parent) 
        self.editor = widget.SelectionWidget()


    def get_widget(self):
        """Overload from Plugin
        
        Returns:
            QWidget
        """
        return self.editor

    def on_open_project(self, conn):
        """Overload from Plugin
        
        Arguments:
            conn 
        """
        self.editor.conn = conn

  



if __name__ == "__main__":
    
    app = QApplication(sys.argv)

    p = SelectionPlugin()

    w = p.get_widget()

    w.show()


    app.exec_()