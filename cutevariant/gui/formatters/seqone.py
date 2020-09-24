# Standard imports
import re

# Qt imports
from PySide2.QtGui import QColor, QFont, QBrush, QPainter, QPen, QFontMetrics
from PySide2.QtCore import Qt, QModelIndex, QRect
from PySide2.QtWidgets import QStyleOptionViewItem

# Custom imports
from cutevariant.gui.formatter import Formatter
from cutevariant.gui import FIcon


class SeqoneFormatter(Formatter):

    DISPLAY_NAME = "Challenger"

    BASE_COLOR = {"A": "green", "C": "red", "G": "black", "T": "red"}

    SO_COLOR = {
        # https://natsukis.livejournal.com/2048.html
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

    IMPACT_COLOR = {
        "HIGH": "#ff4b5c",
        "LOW": "#056674",
        "MODERATE": "#ecad7d",
        "MODIFIER": "#ecad7d",
    }

    FAV_ICON = {0: FIcon(0xF00C3), 1: FIcon(0xF00C0)}

    GENOTYPE_ICONS = {0: FIcon(0xF0766), 1: FIcon(0xF0AA1), 2: FIcon(0xF0AA5), -1: FIcon(0xF10D3)}

    def __init__(self):
        super().__init__()

    def paint(
        self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex
    ):

        brush = QBrush()
        pen = QPen()
        font = QFont()

        field_name = self.field_name(index).lower()
        value = self.value(index)

        if field_name == "ref" or field_name == "alt" and value in ("A", "C", "G", "T"):
            pen.setColor(self.BASE_COLOR.get(value, "black"))

        if field_name == "impact":
            font.setBold(True)
            pen.setColor(self.IMPACT_COLOR.get(value, self.IMPACT_COLOR["MODIFIER"]))

        if field_name == "gene":
            pen.setColor("#6a9fca")

        if field_name == "classification":
            icon = self.ACMG_ICON.get(str(value), self.ACMG_ICON["0"])
            self.draw_icon(painter, option.rect, icon)
            return

        if field_name == "favorite":
            icon = self.FAV_ICON.get(int(value), self.FAV_ICON[0])
            self.draw_icon(painter, option.rect, icon)
            return

        if field_name == "hgvs_c":
            font.setBold(True)
            m = re.search(r"([cnm]\..+)", str(value))
            if m:
                value = m.group(1)

        if field_name == "hgvs_p":
            font.setBold(True)
            m = re.search(r"(p\..+)", str(value))
            if m:
                value = m.group(1)

        if re.match(r"sample\..+\.gt", field_name):
            icon = self.GENOTYPE_ICONS.get(int(value), self.GENOTYPE_ICONS[0])
            self.draw_icon(painter, option.rect, icon)
            return

        if field_name == "consequence":
            values = str(self.value(index)).split("&")
            metrics = QFontMetrics(font)
            x = option.rect.x() + 5
            # y = option.rect.center().y()
            for value in values:
                width = metrics.width(value)
                height = metrics.height()
                rect = QRect(x, 0, width + 15, height + 10)
                rect.moveCenter(option.rect.center())
                rect.moveLeft(x)
                painter.setFont(font)
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
        painter.drawText(option.rect, option.displayAlignment, value)
