"""Plugin to Display genotypes variants 
"""
import typing
from functools import partial
import time
import copy
import re

# Qt imports
from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtWebEngineWidgets import *
from PySide6.QtWebEngineCore import *

# Custom imports
from cutevariant.core import sql, command
from cutevariant.core.reader import BedReader
from cutevariant.gui import plugin, FIcon, style
from cutevariant.constants import DEFAULT_SELECTION_NAME


class IgvView(QWebEngineView):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.settings().setAttribute(QWebEngineSettings.LocalStorageEnabled, True)
        self.settings().setAttribute(QWebEngineSettings.FullScreenSupportEnabled, True)
        self.settings().setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, True)
        # self.settings().setAttribute(QWebEngineSettings.Accelerated2dCanvasEnabled, False)

        self.load("https://igv.org/app/")
        # self.setUrl("https://www.google.com")

    def set_position(self, location):

        self.page().runJavaScript(
            f"""

            $(".igv-search-input").val('{location}')
            $(".igv-search-icon-container").trigger("click")

            """
        )


class IgvWidget(plugin.PluginWidget):
    """Plugin to show all annotations of a selected variant"""

    ENABLE = False
    REFRESH_STATE_DATA = {"current_variant"}

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowIcon(FIcon(0xF070F))

        self.view = IgvView(parent)
        # self.browser = QWebEngineView()
        # self.browser.setUrl(QUrl("http://www.google.fr/"))
        self.vlayout = QVBoxLayout()
        self.vlayout.addWidget(self.view)
        # self.vlayout.addWidget(self.browser)
        self.setLayout(self.vlayout)

    def on_refresh(self):
        variant = self.mainwindow.get_state_data("current_variant")
        variant = sql.get_variant(self.mainwindow.conn, variant["id"])

        chrom = variant["chr"]
        pos = variant["pos"]

        location = f"{chrom}:{pos}"

        self.view.set_position(location)


if __name__ == "__main__":

    import sqlite3
    import sys
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    conn = sqlite3.connect("/home/sacha/test.db")
    conn.row_factory = sqlite3.Row

    view = IgvWidget()
    view.on_open_project(conn)

    view.show()

    app.exec()
