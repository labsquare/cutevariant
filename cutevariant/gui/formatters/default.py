from PySide2.QtGui import (
    QColor,
    QFont,
    QBrush,
    QFontMetrics,
    QIcon,
    QPalette,
    QPixmap,
    QPainter,
    Qt,
    QPen,
)
from PySide2.QtCore import QCoreApplication
from PySide2.QtWidgets import QApplication

import functools
import re

from cutevariant.gui.formatter import Formatter
from cutevariant.gui import FIcon, style


class DefaultFormatter(Formatter):
    def __init__(self):
        return super().__init__()

  
