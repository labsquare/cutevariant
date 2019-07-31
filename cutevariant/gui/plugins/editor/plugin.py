from cutevariant.gui import plugin

from PySide2.QtWidgets import *
import sys 
import sqlite3

from cutevariant.gui.plugins.editor import widget

class EditorPlugin(plugin.Plugin):
    def __init__(self, parent = None):
        super().__init__(parent) 
        self.editor = widget.VqlEditor()
        self.dockable = False

  
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

    def on_query_model_changed(self):
        print("model changed")
        self.editor.set_vql(self.mainwindow.query_widget.model.query.to_vql())


    



if __name__ == "__main__":
    
    app = QApplication(sys.argv)

    p = EditorPlugin()

    w = p.get_widget()

    w.show()


    app.exec_()