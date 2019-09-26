from PySide2.QtGui import QColor, QFont, QIcon, QPalette
from PySide2.QtWidgets import qApp

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

        if re.match(r"genotype(.+).gt", column):
            return "red"


    @functools.lru_cache(maxsize=128)
    def get_decoration(self, column, value):
        if column == "favorite":
            if bool(int(value)) == 1:
                return QIcon(FIcon(0Xf0c1,qApp.palette("QWidget").color(QPalette.Highlight)))
            else:
                return QIcon(FIcon(0xf0c3))

        if column == "classification":
            value = int(value)
            if value == 0:
                return QIcon(FIcon(0xf3a1,"gray"))
            if value == 1:
                return QIcon(FIcon(0xf3a4,style.DARK_COLOR["green"]))
            if value == 2:
                return QIcon(FIcon(0xf3a7,style.DARK_COLOR["green"]))
            if value == 3:
                return QIcon(FIcon(0xf3aa,style.DARK_COLOR["yellow"]))
            if value == 4:
                return QIcon(FIcon(0xf3ad,style.DARK_COLOR["red"]))
            if value == 5:
                return QIcon(FIcon(0xf3b0,style.DARK_COLOR["red"]))    

        if re.match(r"genotype(.+).gt", column):
            value = int(value)
            if value == 0:
                return QIcon(FIcon(0xF130))
            if value == 1:
                return QIcon(FIcon(0xFAA0))
            if value == 2:
                return QIcon(FIcon(0xFAA4))



