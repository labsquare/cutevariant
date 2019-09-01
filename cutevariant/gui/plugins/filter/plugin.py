from cutevariant.gui import plugin

from PySide2.QtWidgets import *
import sys
import sqlite3

from cutevariant.gui.plugins.filter import widget
from cutevariant import commons as cm

LOGGER = cm.logger()


class FilterPlugin(plugin.Plugin):
    Name = "Filter"
    Description = "A plugin to filter variants"
    def __init__(self, parent=None):
        super().__init__(parent)
        self.view = widget.FilterWidget()
        self.view.model.filtersChanged.connect(self.on_filters_changed)

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

    def on_filters_changed(self):
        """ methods called by self.view.model.filterchanged """

        self.mainwindow.query_widget.model.filters = self.view.filters
        self.mainwindow.query_widget.model.load()

    def on_query_model_changed(self):
        self.view.filters = self.mainwindow.query_widget.model.filters


if __name__ == "__main__":

    app = QApplication(sys.argv)

    p = FilterPlugin()

    w = p.get_widget()

    w.show()

    app.exec_()
