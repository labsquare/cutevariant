from PySide2.QtCore import Qt,QModelIndex,QRect
from PySide2.QtWidgets import QStyleOptionViewItem
from PySide2.QtGui import QFont, QIcon, QColor, QPainter
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

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex):


        painter.drawText(option.rect, option.displayAlignment, self.value(index))

    def field_name(self,index: QModelIndex):
        return index.model().headerData(index.column(), Qt.Horizontal)

    def value(self, index: QModelIndex):
        return index.data(Qt.DisplayRole)

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
