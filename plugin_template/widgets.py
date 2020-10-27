

from cutevariant.gui.plugin import PluginWidget
from cutevariant.core.sql import get_sql_connection

class WordSetWidget(PluginWidget):
    """Plugin to show all annotations of a selected variant"""

    ENABLE = True

    def __init__(self, conn=None):
        super().__init__()
        self.conn = conn
        self.setWindowTitle(self.tr("Word Set"))


    def on_open_project(self, conn):
        self.conn = conn
        self.on_refresh()

    def on_refresh(self):
        print("refresh")
  

if __name__ == "__main__":
    import sys
    from PySide2.QtWidgets import QApplication

    app = QApplication(sys.argv)

    conn = get_sql_connection("test.db")

    w = WordSetWidget()
    w.conn = conn

    w.show()

    app.exec_()
