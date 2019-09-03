from cutevariant.gui import plugin
import sqlite3

from cutevariant.gui.plugins.selection import widget


class SelectionPlugin(plugin.Plugin):
    Name = "Selection"
    Description = "A plugin to manage selection and set operation"
    def __init__(self, parent=None):
        super().__init__(parent)
        self.editor = widget.SelectionWidget()
        self.editor.selectionChanged.connect(self.on_selection_changed)

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
        self.editor.selection = self.mainwindow.query_widget.model.selection
        self.editor.load()

    def on_selection_changed(self):
        self.mainwindow.query_widget.model.selection = self.editor.selection
        self.mainwindow.query_widget.model.load()

if __name__ == "__main__":
    from PySide2.QtWidgets import QApplication
    import sys 
    from cutevariant.core.sql import get_sql_connexion


    app = QApplication(sys.argv)

    p = SelectionPlugin()

    w = p.get_widget()

    w.show()

    app.exec_()
