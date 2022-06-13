# Standard imports
import importlib
import pkgutil
import os
import inspect

# Qt imports
from PySide6.QtCore import Qt, QModelIndex, QRect, QUrl
from PySide6.QtWidgets import QStyleOptionViewItem, QItemDelegate, QStyle
from PySide6.QtGui import QIcon, QPainter, QFont, QPen, QColor, QPalette


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


class FormatterDelegate(QItemDelegate):
    """Specify the aesthetic (style and color) of variants displayed on a view"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._formatter = None

    def set_formatter(self, formatter):
        self._formatter = formatter

    def paint(self, painter, option, index):
        """Paint with formatter if defined"""

        if self._formatter is None:
            return super().paint(painter, option, index)

        # Draw selections
        if option.state & QStyle.State_Enabled:
            bg = (
                QPalette.Normal
                if option.state & QStyle.State_Active or option.state & QStyle.State_Selected
                else QPalette.Inactive
            )
        else:
            bg = QPalette.Disabled

        # classification = index.model().variant(index.row())["classification"]

        if option.state & QStyle.State_Selected:
            painter.fillRect(option.rect, option.palette.color(bg, QPalette.Highlight))

        bg_color = index.data(Qt.BackgroundRole)
        if bg_color:
            painter.fillRect(option.rect, bg_color)

            # elif classification > 0:

            # Get color from config .. shortcut
            # item = next(i for i in index.model().classifications if i["number"] == classification)
        # else:
        # color: QColor = QColor(item.get("color", "black"))
        # color.setAlpha(50)
        # painter.fillRect(option.rect, color)

        # Draw formatters
        option.rect = option.rect.adjusted(
            3, 0, 0, 0
        )  # Don't know why I need to adjust the left margin ..

        field_name = index.model().headerData(index.column(), Qt.Horizontal, Qt.DisplayRole)
        field_value = index.data(Qt.DisplayRole)
        is_selected = option.state & QStyle.State_Selected
        style = self._formatter.format(field_name, field_value, option, is_selected)

        font = style.get("font", QFont())
        text = style.get("text", str(field_value))
        icon = style.get("icon", None)
        color = style.get("color")

        if color is None:
            color = option.palette.color(QPalette.BrightText if is_selected else QPalette.Text)

        text_align = style.get("text-align", Qt.AlignVCenter | Qt.AlignLeft)
        icon_align = style.get("icon-align", Qt.AlignCenter)

        pixmap = style.get("pixmap", None)
        link = style.get("link", None)

        if pixmap:
            painter.drawPixmap(
                option.rect.x(),
                option.rect.y(),
                pixmap.width(),
                pixmap.height(),
                pixmap,
            )
            return

        if link:
            self.draw_url(painter, option.rect, text, text_align)
            return

        if icon:
            self.draw_icon(painter, option.rect, icon, icon_align)

        painter.setFont(font)
        painter.setPen(QPen(color))
        painter.drawText(option.rect, text_align, text)

    def draw_icon(self, painter: QPainter, rect: QRect, icon: QIcon, alignement=Qt.AlignCenter):
        r = QRect(0, 0, rect.height(), rect.height())
        r.moveCenter(rect.center())

        if alignement & Qt.AlignLeft:
            r.moveLeft(rect.left())

        if alignement & Qt.AlignRight:
            r.moveRight(rect.right())

        painter.drawPixmap(r, icon.pixmap(r.width(), r.height()))

    def draw_url(self, painter: QPainter, rect: QRect, value: str, align=Qt.AlignLeft):
        font = QFont()
        font.setUnderline(True)
        painter.setFont(font)
        painter.setPen(QPen(QColor("blue")))
        painter.drawText(rect, align, value)

    # def editorEvent(self, event: QEvent, model, option, index: QModelIndex):
    #     return


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
        spec = importlib.util.spec_from_file_location(package.name, package_path + ".py")
        module = spec.loader.load_module()

        for name, obj in inspect.getmembers(module):
            # if the object is a class, whether built-in or created
            # => same as isinstance(obj, type)
            # + test parent class (Formatter)
            if inspect.isclass(obj) and "Formatter" in str(obj.__bases__):
                yield obj


if __name__ == "__main__":
    find_formatters()
