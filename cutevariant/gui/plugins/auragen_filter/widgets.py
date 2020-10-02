from PySide2.QtWidgets import QVBoxLayout

from cutevariant.gui.plugin import PluginWidget
from cutevariant.core.sql import get_sql_connexion
from cutevariant.gui.widgets.filters import (
    FiltersEditor,
    StringFilterWidget,
    ChoiceFilterWidget,
    IntegerFilterWidget,
)


class AuragenFilterWidget(PluginWidget):
    """Plugin to show all annotations of a selected variant"""

    ENABLE = False

    def __init__(self, parent=None):
        super().__init__(parent)
        self.editor = FiltersEditor()

        self.vlayout = QVBoxLayout()
        self.vlayout.addWidget(self.editor)
        self.setLayout(self.vlayout)

        elements = {
            "tabs": [
                {
                    "name": "tab1",
                    "sections": [
                        {
                            "name": "section1",
                            "widgets": [
                                {
                                    "name": "chr",
                                    "description": "editeur de truc",
                                    "widget": IntegerFilterWidget("chr"),
                                },
                                {
                                    "name": "gene",
                                    "description": "editeur de truc",
                                    "widget": StringFilterWidget("gene"),
                                },
                                {
                                    "name": "Impact",
                                    "description": "editeur de truc",
                                    "widget": ChoiceFilterWidget("impact"),
                                },
                                {
                                    "name": "consequence",
                                    "description": "editeur de truc",
                                    "widget": StringFilterWidget("consequence"),
                                },
                            ],
                        }
                    ],
                }
            ]
        }

        self.editor.set_layout_elements(elements)

        self.editor.changed.connect(self.on_changed)

    def on_open_project(self, conn):
        """This method is called when a project is opened

        You should use the sql connector if your plugin uses the SQL database.

        Args:
            conn (sqlite3.connection): A connection to the sqlite project
        """
        self.conn = conn
        self.editor.setup(self.conn)
        self.on_refresh()

    def on_refresh(self):
        """Called to refresh the GUI of the current plugin

        This is called by the mainwindow.controller::refresh methods
        """
        self.editor.reset()

    def on_changed(self):
        """Send current filters to mainwindow and apply them by refreshing the plugins"""
        self.mainwindow.state.filters = self.editor.get_filters()
        self.mainwindow.refresh_plugins(sender=self)


if __name__ == "__main__":
    import sys
    from PySide2.QtWidgets import QApplication

    app = QApplication(sys.argv)

    conn = get_sql_connexion("test.db")

    w = AuragenFilterWidget()
    w.conn = conn

    w.show()

    app.exec_()
