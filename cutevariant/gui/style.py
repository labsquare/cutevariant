"""A place to store style rules for the GUI"""
from logging import Logger
from PySide6.QtWidgets import QProxyStyle, QPushButton, QToolBar, QToolButton
from cutevariant import LOGGER
from cutevariant.constants import DIR_STYLES
from PySide6.QtGui import QPalette, QColor
from cutevariant.commons import camel_to_snake

from PySide6.QtWidgets import QApplication, QSplashScreen, QStyleFactory, QStyle, QProxyStyle
from PySide6.QtGui import *
from PySide6.QtCore import *

from cutevariant.gui.ficon import FIcon

import yaml


class AppStyle(QProxyStyle):
    PALETTE_KEYS = {}

    def __init__(self):
        super().__init__(QStyleFactory.create("fusion"))

        self.theme = {}
        self._colors = {}
        AppStyle.PALETTE_KEYS = {camel_to_snake(k): v for k, v in QPalette.ColorRole.values.items()}
        self.load_theme("dark.yaml")

    def load_theme(self, filename: str):

        with open(DIR_STYLES + filename, "r") as file:
            self.theme = yaml.safe_load(file)

            if "colors" in self.theme["palette"]:
                self._colors = self.theme["palette"]["colors"]

    def colors(self):
        """return color lists"""
        return self._colors

    def polish(self, value):
        """override"""

        if isinstance(value, QPalette):
            cols = self.theme["palette"]["normal"]
            for key, col in cols.items():
                if key in AppStyle.PALETTE_KEYS:
                    role = AppStyle.PALETTE_KEYS[key]
                    value.setColor(role, QColor(col))

    def drawPrimitive(self, element, option, painter, widget) -> None:

        if element == QStyle.PE_PanelToolBar:
            return

        if element == QStyle.PE_IndicatorCheckBox:
            op = option

            #            op.icon = FIcon(0xF0143)
            # op.iconSize = QSize(50, 50)
            color = op.palette.color(QPalette.Text)
            painter.setPen(QPen(color))
            painter.drawRect(option.rect)

            check = option.rect.adjusted(2, 2, -2, -2)
            check.moveCenter(option.rect.center())

            if op.state & QStyle.State_On:
                painter.setBrush(color)
                # painter.setPen(Qt.NoPen)
                painter.drawRect(check)

            return

        # painter.setBrush(QBrush(QColor("red")))

        return super().drawPrimitive(element, option, painter, widget)
