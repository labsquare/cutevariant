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

    IMPACT_COLOR = {
        "LOW": "#71E096",
        "MODERATE": "#F5A26F",
        "HIGH": "#ed6d79",
        "MODIFIER": "#55abe1",
    }

    GENE_COLOR = "#F5A26F"

    def __init__(self):
        return super().__init__()

    def get_display(self, column, value):

        #  Hide genotype texte
        if re.match(r"sample\..+\.gt", column):
            return ""

        return super().get_display(column, value)

    @functools.lru_cache(maxsize=128)
    def get_font(self, column, value):
        return QFont()

    @functools.lru_cache(maxsize=128)
    def get_background(self, column, value):
        return None

    @functools.lru_cache(maxsize=128)
    def get_foreground(self, column, value):
        if "gene" in column:
            return QColor(self.GENE_COLOR)

        # Draw cell depending column name
        if "impact" in column:
            return QColor(self.IMPACT_COLOR[value])

    @functools.lru_cache(maxsize=128)
    def get_decoration(self, column, value):
        if column == "favorite":
            if bool(int(value)) == 1:

                return QIcon(
                    FIcon(
                        0xF00C0,
                        QApplication.instance()
                        .palette("QWidget")
                        .color(QPalette.Highlight),
                    )
                )
            else:
                return QIcon(FIcon(0xF00C3))

        if column == "classification":
            value = int(value)
            if value == 0:
                return QIcon(FIcon(0xF3A1, "gray"))
            if value == 1:
                return QIcon(FIcon(0xF3A4, style.DARK_COLOR["green"]))
            if value == 2:
                return QIcon(FIcon(0xF3A7, style.DARK_COLOR["green"]))
            if value == 3:
                return QIcon(FIcon(0xF3AA, style.DARK_COLOR["yellow"]))
            if value == 4:
                return QIcon(FIcon(0xF3AD, style.DARK_COLOR["red"]))
            if value == 5:
                return QIcon(FIcon(0xF3B0, style.DARK_COLOR["red"]))

        if re.match(r"sample\..+\.gt", column):
            value = int(value)
            if value == 0:
                return QIcon(FIcon(0xF0766))
            elif value == 1:
                return QIcon(FIcon(0xF0AA1))
            elif value == 2:
                return QIcon(FIcon(0xF0AA5))
            return QIcon(FIcon(0xF10D3))

        # if column == "count":

        #     pixmap = QPixmap(32, 32)
        #     pixmap.fill(Qt.transparent)

        #     painter = QPainter(pixmap)
        #     painter.setBrush(
        #         QApplication.instance().palette("QWidget").color(QPalette.Highlight)
        #     )
        #     painter.setPen(Qt.transparent)
        #     rect = pixmap.rect().adjusted(2, 8, -2, -8)
        #     painter.drawRoundedRect(rect, 3, 3)
        #     painter.setPen(QPen(QColor("lightgray")))
        #     painter.drawText(rect, Qt.AlignCenter | Qt.AlignVCenter, str(value))
        #     return pixmap
