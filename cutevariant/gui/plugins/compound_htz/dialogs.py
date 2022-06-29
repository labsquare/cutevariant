import sqlite3

from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtWidgets import *

from cutevariant.gui.plugin import PluginDialog
from cutevariant.gui import MainWindow

class CompoundHtzDialog(PluginDialog):
    """Model class for all tool menu plugins

    These plugins are based on DialogBox; this means that they can be opened
    from the tools menu.
    """

    ENABLE = True

    def __init__(self, conn: sqlite3.Connection, parent: MainWindow=None):
        """
        Keys:
            parent (QMainWindow): cutevariant Mainwindow
        """
        super().__init__(parent)

        self.conn = conn

        self.vlayout = QVBoxLayout()
        self.button = QPushButton("hello")
        self.button.clicked.connect(self.on_click)

        self.vlayout.addWidget(self.button)
        self.setLayout(self.vlayout)



    def on_click(self):
    	print("I'm using this sqlite connection", self.conn)

if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    dialog = CompoundHtzDialog()
    # conn = sqlite3.connect("path_to_test_database.db")
    # conn.row_factory = sqlite3.Row
    # dialog.conn = conn
    dialog.exec_()