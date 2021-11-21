"""Plugin to Display genotypes variants 
"""
import typing
from functools import partial
import time
import copy
import re

# Qt imports
from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWebEngineWidgets import *


# Custom imports
from cutevariant.core import sql, command
from cutevariant.core.reader import BedReader
from cutevariant.gui import plugin, FIcon, style
from cutevariant.commons import DEFAULT_SELECTION_NAME


class IgvView(QWebEngineView):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.settings().setAttribute(
            QWebEngineSettings.LocalContentCanAccessRemoteUrls, True
        )

        self.settings().setAttribute(QWebEngineSettings.LocalStorageEnabled, True)
        self.settings().setAttribute(QWebEngineSettings.FullScreenSupportEnabled, True)

        self.settings().setAttribute(
            QWebEngineSettings.LocalContentCanAccessRemoteUrls, True
        )

        self.load("https://igv.org/app/")

    def set_position(self, location):

        self.page().runJavaScript(
            f"""

            $(".igv-search-input").val('{location}')
            $(".igv-search-icon-container").trigger("click")


            """
        )


class IgvWidget(plugin.PluginWidget):
    """Widget displaying the list of avaible selections.
    User can select one of them to update Query::selection
    """

    ENABLE = True
    REFRESH_STATE_DATA = {"current_variant"}

    def __init__(self, parent=None, conn=None):
        """
        Args:
            parent (QWidget)
            conn (sqlite3.connexion): sqlite3 connexion
        """
        super().__init__(parent)

        self.main_layout = QVBoxLayout(self)
        self.view = IgvView()
        self.main_layout.addWidget(self.view)

    def on_refresh(self):

        variant = self.mainwindow.get_state_data("current_variant")
        variant = sql.get_one_variant(self.mainwindow.conn, variant["id"])

        chrom = variant["chr"]
        pos = variant["pos"]

        location = f"{chrom}:{pos}"

        self.view.set_position(location)


if __name__ == "__main__":

    import sqlite3
    import sys
    from PySide2.QtWidgets import QApplication

    app = QApplication(sys.argv)

    conn = sqlite3.connect("/DATA/dev/cutevariant/corpos2.db")
    conn.row_factory = sqlite3.Row

    view = IgvWidget()
    view.on_open_project(conn)
    view.show()

    app.exec_()
