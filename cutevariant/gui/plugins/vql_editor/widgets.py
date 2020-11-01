"""Exposes VqlEditor class used in the MainWindow to show VQL statements.
VqlEditor uses:
    - VqlSyntaxHighlighter as a syntax highlighter
    - VqlEdit for the support of autocompletion

Warnings:
    When you add a VQL command in the language, please update
    :meth:`VqlEditorWidget.run_vql` method in consequence. Otherwise no command
    will be executed.
"""
# Standard imports
from textx.exceptions import TextXSyntaxError
import sqlite3

# Qt imports
from PySide2.QtCore import Qt, QStringListModel
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
from cutevariant.core import command
from cutevariant.core.querybuilder import build_vql_query
from cutevariant.gui.widgets import VqlEditor, VqlSyntaxHighlighter
from cutevariant.commons import logger

LOGGER = logger()


class VqlEditorWidget(plugin.PluginWidget):
    """Exposed class to manage VQL/SQL queries from the mainwindow"""

    LOCATION = plugin.FOOTER_LOCATION
    ENABLE = True

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("VQL Editor"))

        # Top toolbar
        self.top_bar = QToolBar()
        self.top_bar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.run_action = self.top_bar.addAction(
            FIcon(0xF040A), self.tr("Run"), self.run_vql
        )
        self.run_action.setShortcuts([Qt.CTRL + Qt.Key_R, QKeySequence.Refresh])
        self.run_action.setToolTip(self.tr("Run VQL query (F5)"))

        # Syntax highlighter and autocompletion
        self.text_edit = VqlEditor()
        self.highlighter = VqlSyntaxHighlighter(self.text_edit.document())
        # Error handling
        self.log_edit = QLabel()
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
        self.text_edit.setCompleter(self._create_completer())

        self.on_refresh()

    def on_refresh(self):
        """overrided from PluginWidget"""

        vql_query = build_vql_query(
            self.mainwindow.state.fields,
            self.mainwindow.state.source,
            self.mainwindow.state.filters,
            self.mainwindow.state.group_by,
            self.mainwindow.state.having,
        )

        self.set_vql(vql_query)

    def set_vql(self, text: str):
        """Set vql source code without executed

        Args:
            text (str): VQL query
        """
        self.text_edit.blockSignals(True)
        self.text_edit.setPlainText(text)
        self.text_edit.blockSignals(False)

    def _create_completer(self):
        """Create Completer with his model

        Fill the model with the SQL keywords and database fields
        """
        model = QStringListModel()
        completer = QCompleter()

        keywords = []
        samples = [i["name"] for i in sql.get_samples(self.conn)]
        selections = [i["name"] for i in sql.get_selections(self.conn)]
        for field in sql.get_fields(self.conn):
            if field["category"] == "samples":
                for sample in samples:
                    keywords.append("sample['{}'].{}".format(sample, field["name"]))
            else:
                keywords.append(field["name"])

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
            bool: Status of VQL query (True if valid, False otherwise).
        """
        try:
            self.log_edit.hide()
            _ = [i for i in vql.parse_vql(self.text_edit.toPlainText())]
        except (TextXSyntaxError, VQLSyntaxError) as e:
            # Show the error message on the ui
            # Available attributes: e.message, e.line, e.col
            self.set_message(
                "%s: %s, col: %d" % (e.__class__.__name__, e.message, e.col)
            )
            return False
        return True

    def run_vql(self):
        """Execute VQL code

        Suported commands and the plugins that need to be refreshed in consequence:
            - select_cmd: main ui (all plugins in fact)
            - count_cmd: *not supported*
            - drop_cmd: selections & wordsets
            - create_cmd: selections
            - set_cmd: selections
            - bed_cmd: selections
            - show_cmd: *not supported*
            - import_cmd: wordsets
        """
        # Check VQL syntax first
        if not self.check_vql():
            return

        for cmd in vql.parse_vql(self.text_edit.toPlainText()):

            LOGGER.debug("VQL command %s", cmd)
            cmd_type = cmd["cmd"]

            # If command is a select kind
            if cmd_type == "select_cmd":
                # => Command will be executed in different widgets (variant_view)
                # /!\ VQL Editor will not check SQL validity of the command
                # columns from variant table
                self.mainwindow.state.fields = cmd["fields"]
                # name of the variant selection
                self.mainwindow.state.source = cmd["source"]
                self.mainwindow.state.filters = cmd["filters"]
                self.mainwindow.state.group_by = cmd["group_by"]
                self.mainwindow.state.having = cmd["having"]
                # Refresh all plugins
                self.mainwindow.refresh_plugins(sender=self)
                continue

            try:
                # Check SQL validity of selections related commands
                command.create_command_from_obj(self.conn, cmd)()
            except (sqlite3.DatabaseError, VQLSyntaxError) as e:
                # Display errors in VQL editor
                self.set_message(str(e))
                LOGGER.exception(e)
                continue

            # Selections related commands
            if cmd_type in ("create_cmd", "set_cmd", "bed_cmd"):
                # refresh source editor plugin for selections
                self.mainwindow.refresh_plugin("source_editor")
                continue

            if cmd_type == "drop_cmd":
                # refresh source editor plugin for selections
                self.mainwindow.refresh_plugin("source_editor")
                # refresh wordset plugin
                self.mainwindow.refresh_plugin("word_set")

            if cmd_type == "import_cmd":
                # refresh wordset plugin
                self.mainwindow.refresh_plugin("word_set")

    def set_message(self, message: str):
        """Show message error at the bottom of the view

        Args:
            message (str): Error message
        """
        if self.log_edit.isHidden():
            self.log_edit.show()

        icon_64 = FIcon(0xF0027, style.WARNING_TEXT_COLOR).to_base64(18, 18)

        self.log_edit.setText(
            """<div height=100%>
            <img src="data:image/png;base64,{}" align="left"/>
             <span> {} </span>
            </div>""".format(icon_64, message)
        )


if __name__ == "__main__":

    import sys

    app = QApplication(sys.argv)

    conn = sqlite3.connect("examples/test.db")

    view = VqlEditorWidget()
    view.show()

    app.exec_()
