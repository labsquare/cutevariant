"""Expose MainWindow class and a handy FIcon class used to display icons
from the font set by setFontPath function"""
from .ficon import FIcon, setFontPath
from .mainwindow import MainWindow

from .formatter import Formatter, FormatterDelegate

# Weird bug : if we exchange these two lines it creates a circular reference with FIcon...
