
from PySide2.QtCore import Qt
from PySide2.QtGui import QFont, QIcon, QColor
import functools
from cutevariant.gui.ficon import FIcon

class Formatter(object):

    GENE_COLOR = "#F5A26F"


    def __init__(self):
        super().__init__()
        self.caches = []
        self.columns = []

    @functools.lru_cache(maxsize=128)
    def get_font(self, column, value):
        return QFont()
    
    @functools.lru_cache(maxsize=128)
    def get_background(self, column, value):
        if column == "ref" and value == "A":
            return QColor("red")
        return None

    @functools.lru_cache(maxsize=128)
    def get_foreground(self, column, value):
        if "gene" in column:
            return QColor(self.GENE_COLOR)

    @functools.lru_cache(maxsize=128)
    def get_decoration(self, column, value):
        if column == "favorite":
            if bool(int(value)) == 1:
                return QIcon(FIcon(0Xf855))
            else:
                return QIcon(FIcon(0xf131))


    def item_data(self,column_name, value, role : Qt.ItemDataRole):

        if role == Qt.FontRole:
            return self.get_font(column_name, value)

        if role == Qt.BackgroundRole:
            return self.get_background(column_name,value)

        if role == Qt.ForegroundRole:
            return self.get_foreground(column_name,value)

        if role == Qt.TextColorRole:
            return self.get_textcolor(column_name,value)
        
        if role == Qt.DecorationRole:
            return self.get_decoration(column_name,value)

        return None

    def supported_role(cls):
        return (Qt.FontRole, Qt.BackgroundRole, Qt.ForegroundRole, Qt.DecorationRole)