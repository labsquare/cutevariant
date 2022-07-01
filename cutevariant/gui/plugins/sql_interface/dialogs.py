import sqlite3
import typing

from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtWidgets import *

from cutevariant.core import sql
from cutevariant.gui.plugin import PluginDialog
from cutevariant.gui import MainWindow

class SqlInterfaceDialog(PluginDialog):
    """Model class for all tool menu plugins

    These plugins are based on DialogBox; this means that they can be opened
    from the tools menu.
    """

    ENABLE = True

    def __init__(self, conn: sqlite3.Connection, parent: MainWindow=None) -> None:
        """
        Keys:
            parent (QMainWindow): cutevariant Mainwindow
        """
        super().__init__(parent)

        self.conn = conn

        group_box = QGroupBox()
        header = QLabel()
        header.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        header.setText("Type your SQL command(s)")
        self.command = QTextEdit()
        self.command.setPlaceholderText("SELECT * from variants WHERE classification = 1;")
        header_layout = QVBoxLayout()
        header_layout.addWidget(header)
        header_layout.addWidget(self.command)
        group_box.setLayout(header_layout)

        self.checkbox = QCheckBox(f"This command will change the database (WARNING: there is no 'undo' button)", self)

        self.button = QPushButton("Execute SQL")
        self.button.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        self.button.clicked.connect(self._on_click)
        button_box = QVBoxLayout()
        button_box.setAlignment(Qt.AlignCenter)
        button_box.addWidget(self.button)

        self.setWindowTitle("SQL interface")
        self.vlayout = QVBoxLayout()
        self.vlayout.addWidget(group_box)
        self.vlayout.addWidget(self.checkbox)
        self.vlayout.addLayout(button_box)
        self.setLayout(self.vlayout)


    def _on_click(self) -> None:
        commands = self.command.toPlainText()
        if ";" in commands:
            cmd_list = commands.split(";")
            if cmd_list[-1] == "":
                del cmd_list[-1]
        else:
            cmd_list = [commands]

        if not self.checkbox.checkState():
            if any([cmd.upper().startswith("SELECT ") != True for cmd in cmd_list]):
                QMessageBox.critical(
                    self, "Unauthorized command", "Can only do SELECT commands without checking the box"
                )
                return

        for cmd in cmd_list:
            print(list(self._execute_sql(cmd)))

    def _execute_sql(self, query) -> typing.Tuple[dict]:
        self.conn.row_factory = sqlite3.Row
        return (dict(data) for data in self.conn.execute(query))


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    conn = sql.get_sql_connection(
        "L:/Archives/NGS/BIO_INFO/BIO_INFO_Sam/scripts/cutevariant_project/devel_june2022.db"
    )
    dialog = SqlInterfaceDialog(conn)
    dialog.exec()