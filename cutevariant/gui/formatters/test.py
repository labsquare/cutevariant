from PySide2.QtGui import QColor, QFont

from cutevariant.gui.formatter import Formatter


class TestFormatter(Formatter):
    def __init__(self):
        return super().__init__()

    def get_background(self, column, value):
        if column == "alt" and value == "A":
            return QColor("green")

        return None
