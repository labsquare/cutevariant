# Standard imports
import importlib
import pkgutil
import os
import inspect

# Qt imports
from PySide2.QtCore import Qt, QModelIndex, QRect
from PySide2.QtWidgets import QStyleOptionViewItem
from PySide2.QtGui import QIcon, QPainter


class Formatter(object):
    """Helper to customize cell style from QueryModel.
    You can set the font, background, foreground and decoration (QIcon)

    Class attributes:
        - DISPLAY_NAME: Name of the formatter displayed on the GUI.
    """
    DISPLAY_NAME = ""

    def __init__(self):
        super().__init__()

    def paint(
        self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex
    ):
        painter.drawText(option.rect, option.displayAlignment, self.value(index))

    def field_name(self, index: QModelIndex):
        return index.model().headerData(index.column(), Qt.Horizontal)

    def value(self, index: QModelIndex):
        return index.data(Qt.DisplayRole)

    def draw_icon(self, painter: QPainter, rect: QRect, icon: QIcon):
        r = QRect(0, 0, 20, 20)
        r.moveCenter(rect.center())
        painter.drawPixmap(r, icon.pixmap(20, 20))


################################################################################


def find_formatters(path=None):
    """Find and return formatter classes from a directory

    Formatters must be found in `cutevariant/gui/formatters/`

    Keyword Arguments:
        path [str] -- the folder path where plugin are

    Returns:
        [generator [Formatter]] -- A Formatter class ready to be instantiated
    """

    # if path is None, return internal plugin path
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
            # if the object is a class, whether built-in or created
            # => same as isinstance(obj, type)
            # + test parent class (Formatter)
            if inspect.isclass(obj) and "Formatter" in str(obj.__bases__):
                yield obj


if __name__ == "__main__":
    find_formatters()
