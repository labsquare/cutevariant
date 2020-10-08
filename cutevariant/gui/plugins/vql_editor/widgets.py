"""Exposes VqlEditor class used in the MainWindow to show SQL statements.
VqlEditor uses:
    - VqlSyntaxHighlighter as a syntax highlighter
    - VqlEdit for the support of autocompletion
"""
# Standard imports
from textx.exceptions import TextXSyntaxError
import sqlite3

# Qt imports
from PySide2.QtCore import Qt, QRegularExpression, QStringListModel, Signal
from PySide2.QtWidgets import (
    QToolBar,
    QCompleter,
    QVBoxLayout,
    QLabel,
    QFrame,
    QApplication,
)
from PySide2.QtGui import QKeySequence

# Custom imports
from cutevariant.core import vql, sql
from cutevariant.gui import style, plugin, FIcon
from cutevariant.core.vql import VQLSyntaxError
from cutevariant.commons import logger
from cutevariant.core import command

from cutevariant.core.querybuilder import build_vql_query


from cutevariant.gui.widgets import VqlEditor, VqlSyntaxHighlighter

LOGGER = logger()


class VqlEditorWidget(plugin.PluginWidget):
    """Exposed class to manage VQL/SQL queries from the mainwindow"""

    LOCATION = plugin.FOOTER_LOCATION
    ENABLE = True

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Vql Editor"))

        # Top toolbar
        self.top_bar = QToolBar()
        self.top_bar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.run_action = self.top_bar.addAction(
            FIcon(0xF040A), self.tr("Run"), self.run_vql
        )
        self.run_action.setShortcuts([Qt.CTRL + Qt.Key_R, QKeySequence.Refresh])

        # Syntax highlighter and autocompletion
        self.text_edit = VqlEditor()
        self.log_edit = QLabel()
        self.highlighter = VqlSyntaxHighlighter(self.text_edit.document())

        self.log_edit.setMinimumHeight(40)
        self.log_edit.setStyleSheet(
            "QWidget{{background-color:'{}'; color:'{}'}}".format(
                style.WARNING_BACKGROUND_COLOR, style.WARNING_TEXT_COLOR
            )
        )
        self.log_edit.hide()

        self.log_edit.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        main_layout = QVBoxLayout()
        main_layout.addWidget(self.top_bar)
        main_layout.addWidget(self.text_edit)
        main_layout.addWidget(self.log_edit)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        self.setLayout(main_layout)

    def on_open_project(self, conn: sqlite3.Connection):
        """overrided from PluginWidget : Do not call this methods

        Args:
            conn (sqlite3.Connection): sqlite3 connection
        """
        self.conn = conn
        self.text_edit.setCompleter(self.__create_completer())

        self.on_refresh()

    def on_refresh(self):
        """overrided from PluginWidget"""

        vql_obj = build_vql_query(
            self.mainwindow.state.fields,
            self.mainwindow.state.source,
            self.mainwindow.state.filters,
            self.mainwindow.state.group_by,
            self.mainwindow.state.having,
        )

        self.set_vql(vql_obj)

    def set_vql(self, txt: str):
        """Set vql source code without executed

        Args:
            txt (str): vql code
        """
        self.text_edit.blockSignals(True)
        self.text_edit.setPlainText(txt)
        self.text_edit.blockSignals(False)

    def __create_completer(self):
        """Create Completer with his model"""
        model = QStringListModel()
        completer = QCompleter()
        # Fill the model with the SQL keywords and database fields

        # fields = [i["name"] for i in sql.get_fields(self.conn)]

        keywords = []
        samples = [i["name"] for i in sql.get_samples(self.conn)]
        selections = [i["name"] for i in sql.get_selections(self.conn)]
        for i in sql.get_fields(self.conn):
            if i["category"] == "samples":
                for s in samples:
                    keywords.append("sample['{}'].{}".format(s, i["name"]))
            else:
                keywords.append(i["name"])

        keywords.extend(VqlSyntaxHighlighter.sql_keywords)
        keywords.extend(selections)
        model.setStringList(keywords)
        completer.setModel(model)
        return completer

    def check_vql(self) -> bool:
        """Check VQL statement; return True if OK, False when an error occurs

        Notes:
            This function also sets the error message to the bottom of the view.

        Returns:
            bool: Status
        """

        try:
            self.log_edit.hide()
            [i for i in vql.parse_vql(self.text_edit.toPlainText())]

        except TextXSyntaxError as e:
            # Available attributes: e.message, e.line, e.col
            self.set_message("TextXSyntaxError: %s, col: %d" % (e.message, e.col))
            return False

        except VQLSyntaxError as e:
            # Show the error message on the ui
            self.set_message(
                self.tr("VQLSyntaxError: '%s' at position %s") % (e.message, e.col)
            )
            return False

        return True

    def run_vql(self):
        """Execute VQL code

        TODO: old doc deleted
        """

        # Check VQL syntax first
        if not self.check_vql():
            return

        for cmd in vql.parse_vql(self.text_edit.toPlainText()):

            #  If command is a select kind
            if cmd["cmd"] == "select_cmd":
                self.mainwindow.state.fields = cmd[
                    "fields"
                ]  # columns from variant table
                self.mainwindow.state.source = cmd["source"]  # name of the variant set
                self.mainwindow.state.filters = cmd["filters"]
                self.mainwindow.state.group_by = cmd["group_by"]
                self.mainwindow.state.having = cmd["having"]
                self.mainwindow.refresh_plugins(sender=self)

            if cmd["cmd"] in ("create_cmd", "set_cmd", "drop_cmd"):
                fct = command.create_command_from_obj(self.conn, cmd)
                fct()

                # refresh source editor plugin
                if "source_editor" in self.mainwindow.plugins:
                    plugin = self.mainwindow.plugins["source_editor"]
                    plugin.on_refresh()

                # TODO : manage other request

    def set_message(self, message: str):
        """Show message error at the bottom of the view

        Args:
            message (str): Description
        """
        if self.log_edit.isHidden():
            self.log_edit.show()

        icon_64 = FIcon(0xF0027, style.WARNING_TEXT_COLOR).to_base64(18, 18)

        self.log_edit.setText(
            """
            <div height=100%>
            <img src="data:image/png;base64,{}" align="left"/>
             <span>  {} </span>
            </div>""".format(
                icon_64, message
            )
        )


if __name__ == "__main__":

    import sys

    app = QApplication(sys.argv)

    conn = sqlite3.connect("examples/test.db")

    view = VqlEditorWidget()
    view.show()

    app.exec_()
