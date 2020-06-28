from PySide2.QtCore import Qt
from PySide2.QtGui import QFont, QIcon, QColor
from cutevariant.gui.ficon import FIcon

import importlib
import pkgutil
import os
import inspect
import functools


class Formatter(object):
    """This class helps you to customize cell style from QueryModel.
    You can set the font, background, foreground and decoration ( QIcon)

    """

    def __init__(self):
        super().__init__()

    @functools.lru_cache(maxsize=128)
    def get_font(self, column, value):
        """Return font for a cell according column name and value
        
        Args:
            column (str): Column name
            value (any): Value of the cell 
        
        Returns:
            QFont: a font
        """
        return None

    @functools.lru_cache(maxsize=128)
    def get_background(self, column, value):
        """Return background color of the cell acording column name and value 
        
        Args:
            column (str):Column name
            value (any):Value of the cell
        
        Returns:
            QColor: A color  
        """
        return None

    @functools.lru_cache(maxsize=128)
    def get_foreground(self, column, value):
        """Return text color of the cell according column name and value
        
        Args:
            column (str): Column name
            value (any): Value of the cell
        
        Returns:
            QColor: A color
        """
        return None

    @functools.lru_cache(maxsize=128)
    def get_decoration(self, column, value):
        """Return decoration as QIcon of the cell according column and value
        
        Args:
            column (str): Column name
            value (any): Value of the cell
        
        Returns:
            QIcon: a Icon. 
            TODO : I guess it can be QPixmap also 
        """
        return None

    def item_data(self, column_name, value, role: Qt.ItemDataRole):
        """Return cell data according column name and value for the specific role
        
        Args:
            column_name (str): Column name
            value (any): Value of the cell
            role (Qt.ItemDataRole): a Qt Role 
        
        Returns:
            any: depending of the role, it can be QColor, QFont or QIcon
        """

        if role == Qt.FontRole:
            return self.get_font(column_name, value)

        if role == Qt.BackgroundRole:
            return self.get_background(column_name, value)

        if role == Qt.ForegroundRole:
            return self.get_foreground(column_name, value)

        if role == Qt.TextColorRole:
            return self.get_textcolor(column_name, value)

        if role == Qt.DecorationRole:
            return self.get_decoration(column_name, value)

        return None

    def supported_role(cls):
        return (Qt.FontRole, Qt.BackgroundRole, Qt.ForegroundRole, Qt.DecorationRole)


def find_formatters(path=None):
    #  if path is None, return internal plugin path
    if path is None:
        formatter_path = os.path.join(os.path.dirname(__file__), "formatters")
    else:
        formatter_path = path

    for package in pkgutil.iter_modules([formatter_path]):
        package_path = os.path.join(formatter_path, package.name)
        spec = importlib.util.spec_from_file_location(
            package.name, package_path + ".py"
        )
        module = spec.loader.load_module()

        for name, obj in inspect.getmembers(module):
            if inspect.isclass(obj):
                if "Formatter" in str(obj.__bases__):
                    yield obj


if __name__ == "__main__":
    find_formatters()
