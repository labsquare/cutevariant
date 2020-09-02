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
    QFontMetrics,
)
from PySide2.QtCore import QModelIndex, QRect, QPoint
from PySide2.QtWidgets import QApplication, QStyleOptionViewItem

import functools
import re

from cutevariant.gui.formatter import Formatter
from cutevariant.gui import FIcon, style


class SeqoneFormatter(Formatter):

    BASE_COLOR = {"A": "green", "C": "red", "G": "black", "T": "red"}

    SO_COLOR = {
        # https://www.google.com/url?sa=i&url=https%3A%2F%2Fnatsukis.livejournal.com%2F2048.html&psig=AOvVaw11r2D9gwnmLeORQjAMr35V&ust=1599144498880000&source=images&cd=vfe&ved=0CAIQjRxqFwoTCPCI_qrNyusCFQAAAAAdAAAAABAD
        "missense_variant": "#bb96ff",
        "synonymous_variant": "#67eebd",
        "stop_gained": "#ed6d79",
        "stop_lost": "#ed6d79",
        "frameshift_variant": "#ff89b5",
    }

    ACMG_ICON = {
        "0": FIcon(0xF03A1, "lightgray"),
        "1": FIcon(0xF03A4, "#71e096"),
        "2": FIcon(0xF03A7, "#71e096"),
        "3": FIcon(0xF03AA, "#f5a26f"),
        "4": FIcon(0xF03AD, "#ed6d79"),
        "5": FIcon(0xF03B1, "#ed6d79"),
    }

    FAV_ICON = {0: FIcon(0xF00C3), 1: FIcon(0xF00C0)}

    def __init__(self):
        return super().__init__()

    def paint(
        self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex
    ):

        brush = QBrush()
        pen = QPen()
        font = QFont()

        field_name = self.field_name(index).lower()
        value = self.value(index)

        if field_name == "ref" or field_name == "alt" and value in ("A", "C", "G", "T"):
            pen.setColor(self.BASE_COLOR[value])

        if field_name == "impact":
            font.setBold(True)
            pen.setColor("#ecad7d")

        if field_name == "gene":
            pen.setColor("#6a9fca")

        if field_name == "classification":

            rect = QRect(0, 0, 20, 20)
            rect.moveCenter(option.rect.center())
            icon = self.ACMG_ICON.get(str(value), self.ACMG_ICON["0"])
            painter.drawPixmap(rect, icon.pixmap(20, 20))
            return

        if field_name == "favorite":
            rect = QRect(0, 0, 20, 20)
            rect.moveCenter(option.rect.center())
            icon = self.FAV_ICON.get(int(value), self.FAV_ICON[0])
            painter.drawPixmap(rect, icon.pixmap(20, 20))
            return

        if field_name == "consequence":
            values = str(self.value(index)).split("&")
            metrics = QFontMetrics(font)
            x = option.rect.x() + 5
            y = option.rect.center().y()
            for value in values:
                width = metrics.width(value)
                height = metrics.height()
                rect = QRect(x, 0, width + 15, height + 10)
                rect.moveCenter(option.rect.center())
                rect.moveLeft(x)

                painter.setClipRect(option.rect, Qt.IntersectClip)
                painter.setBrush(QBrush(QColor(self.SO_COLOR.get(value, "#90d4f7"))))
                painter.setPen(Qt.NoPen)
                painter.drawRoundedRect(rect, 3, 3)
                painter.setPen(QPen(QColor("white")))
                painter.drawText(rect, Qt.AlignCenter | Qt.AlignVCenter, value)
                x += width + 20
                painter.setClipping(False)

            return

        painter.setBrush(brush)
        painter.setPen(pen)
        painter.setFont(font)
        painter.drawText(option.rect, option.displayAlignment, self.value(index))
