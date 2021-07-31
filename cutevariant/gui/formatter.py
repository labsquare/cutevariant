# Standard imports
import importlib
import pkgutil
import os
import inspect

# Qt imports
from PySide2.QtCore import Qt, QModelIndex, QRect, QUrl
from PySide2.QtWidgets import QStyleOptionViewItem
from PySide2.QtGui import QIcon, QPainter, QFont, QPen, QColor


class Formatter(object):
    """Helper to customize cell style from QueryModel.
    You can set the font, background, foreground and decoration (QIcon)

    Class attributes:
        - DISPLAY_NAME: Name of the formatter displayed on the GUI.
    """

    DISPLAY_NAME = ""

    def refresh(self):
        pass

    def format(self, field: str, value: str, option, is_selected: bool = False):

        # return {
        #     "text": str(field_value),
        #     "color": "white",
        #     "background-color": "red",
        #     "alignement": Qt.AlignCenter,
        #     "icon": QIcon(),
        #     "link": "http://www.google.fr",
        #     "pixmap": QPixmap(),
        # }

        return {"text": str(value)}

    # def __init__(self):
    #     super().__init__()

    # def paint(
    #     self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex
    # ):
    #     painter.drawText(option.rect, option.displayAlignment, self.value(index))

    # def field_name(self, index: QModelIndex):
    #     return index.model().headerData(index.column(), Qt.Horizontal)

    # def value(self, index: QModelIndex):
    #     return index.data(Qt.DisplayRole)

    # def draw_icon(self, painter: QPainter, rect: QRect, icon: QIcon):

    #     r = QRect(0, 0, rect.height(), rect.height())
    #     r.moveCenter(rect.center())
    #     painter.drawPixmap(r, icon.pixmap(r.width(), r.height()))

    # def draw_url(self, painter: QPainter, rect: QRect, value: str):
    #     font = QFont()
    #     font.setUnderline(True)
    #     painter.setFont(font)
    #     painter.setPen(QPen(QColor("blue")))
    #     painter.drawText(rect, Qt.AlignCenter, value)


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
