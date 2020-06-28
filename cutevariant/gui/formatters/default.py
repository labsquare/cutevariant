from PySide2.QtGui import QColor, QFont, QIcon, QPalette
from PySide2.QtCore import QCoreApplication
from PySide2.QtWidgets import QApplication

import functools
import re

from cutevariant.gui.formatter import Formatter
from cutevariant.gui import FIcon, style


class DefaultFormatter(Formatter):

    IMPACT_COLOR = {
        "LOW": "#71E096",
        "MODERATE": "#F5A26F",
        "HIGH": "#ed6d79",
        "MODIFIER": "#55abe1",
    }

    GENE_COLOR = "#F5A26F"

    def __init__(self):
        return super().__init__()

    @functools.lru_cache(maxsize=128)
    def get_font(self, column, value):
        return QFont()

    @functools.lru_cache(maxsize=128)
    def get_background(self, column, value):
        return None

    @functools.lru_cache(maxsize=128)
    def get_foreground(self, column, value):
        if "gene" in column:
            return QColor(self.GENE_COLOR)

        # Draw cell depending column name
        if column == "impact":
            return self.IMPACT_COLOR[value]

    @functools.lru_cache(maxsize=128)
    def get_decoration(self, column, value):
        if column == "favorite":
            if bool(int(value)) == 1:

                return QIcon(
                    FIcon(
                        0xF0C1,
                        QApplication.instance()
                        .palette("QWidget")
                        .color(QPalette.Highlight),
                    )
                )
            else:
                return QIcon(FIcon(0xF0C3))

        if column == "classification":
            value = int(value)
            if value == 0:
                return QIcon(FIcon(0xF3A1, "gray"))
            if value == 1:
                return QIcon(FIcon(0xF3A4, style.DARK_COLOR["green"]))
            if value == 2:
                return QIcon(FIcon(0xF3A7, style.DARK_COLOR["green"]))
            if value == 3:
                return QIcon(FIcon(0xF3AA, style.DARK_COLOR["yellow"]))
            if value == 4:
                return QIcon(FIcon(0xF3AD, style.DARK_COLOR["red"]))
            if value == 5:
                return QIcon(FIcon(0xF3B0, style.DARK_COLOR["red"]))

        if re.match(r"genotype(.+).gt", column):
            value = int(value)
            if value == 0:
                return QIcon(FIcon(0xF130))
            elif value == 1:
                return QIcon(FIcon(0xFAA0))
            elif value == 2:
                return QIcon(FIcon(0xFAA4))
            return QIcon(FIcon(0xF2D7))
