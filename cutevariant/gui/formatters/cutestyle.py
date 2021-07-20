# Standard imports
import re

# Qt imports
from PySide2.QtGui import (
    QColor,
    QFont,
    QBrush,
    QPainter,
    QPen,
    QFontMetrics,
    QPalette,
    QPixmap,
)
from PySide2.QtCore import Qt, QModelIndex, QRect, QUrl, QPoint
from PySide2.QtWidgets import QStyleOptionViewItem, QStyle

# Custom imports
from cutevariant.gui.formatter import Formatter
from cutevariant.gui import FIcon
import cutevariant.commons as cm

from cutevariant.config import Config


class CutestyleFormatter(Formatter):

    DISPLAY_NAME = "Cute style"

    BASE_COLOR = {"A": "green", "C": "red", "T": "red"}

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
        "2": FIcon(0xF03A7, "#a7ecbe"),
        "3": FIcon(0xF03AA, "#f5a26f"),
        "4": FIcon(0xF03AD, "#f9cdd1"),
        "5": FIcon(0xF03B1, "#ed6d79"),
    }

    IMPACT_COLOR = {
        "HIGH": "#ff4b5c",
        "LOW": "#056674",
        "MODERATE": "#ecad7d",
        "MODIFIER": "#ecad7d",
    }

    FAV_ICON = {0: FIcon(0xF00C3), 1: FIcon(0xF00C0)}

    # Cache genotype icons
    # Values in gt field as keys (str), FIcon as values
    GENOTYPE_ICONS = {key: FIcon(val) for key, val in cm.GENOTYPE_ICONS.items()}

    def __init__(self):
        self.refresh()

    def refresh(self):
        config = Config("variant_view")
        self.TAGS_COLOR = {tag["name"]: tag["color"] for tag in config.get("tags", [])}

    def format(self, field: str, value: str, option, is_selected):

        if value == "NULL":
            font = QFont()
            font.setItalic(True)
            return {"font": font, "color": "lightgray"}

        if field == "ann.impact" and not is_selected:
            font = QFont()
            font.setBold(True)
            color = self.IMPACT_COLOR.get(value, self.IMPACT_COLOR["MODIFIER"])

            return {"font": font, "color": color}

        #     # Colour bases (default color is the one of the current theme)
        if (field == "ref" or field == "alt") and (
            value in ("A", "C", "G", "T") and not is_selected
        ):
            return {"color": self.BASE_COLOR.get(value)}

        if field == "ann.gene" and not is_selected:
            return {"color": "#6a9fca"}

        if field == "classification":
            icon = self.ACMG_ICON.get(str(value), self.ACMG_ICON["0"])
            return {"icon": icon, "text": "", "icon-align": Qt.AlignCenter}

        if field == "rsid" and value.startswith("rs"):
            # font.setUnderline(True)
            return {"link": "http://www.google.fr"}
            # pen.setColor("#0068F7")

        if field == "favorite":
            icon = self.FAV_ICON.get(int(value), self.FAV_ICON[0])
            return {"icon": icon, "text": "", "icon-align": Qt.AlignCenter}
            return

        if field == "ann.hgvs_c":
            font = QFont()
            font.setBold(True)
            m = re.search(r"([cnm]\..+)", str(value))
            if m:
                value = m.group(1)
                return {"text": value}

        if field == "ann.hgvs_p":
            font = QFont()
            font.setBold(True)
            m = re.search(r"(p\..+)", str(value))
            if m:
                value = m.group(1)
                return {"text": value}

        if re.match(r"samples\..+\.gt", field):
            icon = self.GENOTYPE_ICONS.get(int(value), self.GENOTYPE_ICONS[-1])
            return {"text": "", "icon": icon}

        if field == "ann.consequence":
            values = str(value).split("&")
            font = QFont()
            metrics = QFontMetrics(font)
            x = 0
            # y = option.rect.center().y()
            pix = QPixmap(option.rect.size())
            pix.fill(Qt.transparent)
            painter = QPainter(pix)
            for index, value in enumerate(values):
                width = metrics.width(value)
                height = metrics.height()
                rect = QRect(x, 2, width + 15, height + 10)

                painter.setFont(font)
                # painter.setClipRect(option.rect, Qt.IntersectClip)
                painter.setBrush(QBrush(QColor(self.SO_COLOR.get(value, "#90d4f7"))))
                painter.setPen(Qt.NoPen)
                painter.drawRoundedRect(rect, 3, 3)
                painter.setPen(QPen(QColor("white")))
                painter.drawText(rect, Qt.AlignCenter | Qt.AlignVCenter, value)
                x += width + 20

            return {"pixmap": pix}

        if field == "tags":
            if value is None or value == "":
                return {}

            values = str(value).split("&")
            font = QFont()
            metrics = QFontMetrics(font)
            x = 0
            # y = option.rect.center().y()
            pix = QPixmap(option.rect.size())
            pix.fill(Qt.transparent)
            painter = QPainter(pix)
            for index, value in enumerate(values):
                width = metrics.width(value)
                height = metrics.height()
                rect = QRect(x, 2, width + 15, height + 10)

                painter.setFont(font)
                # painter.setClipRect(option.rect, Qt.IntersectClip)
                painter.setBrush(
                    QBrush(QColor(self.TAGS_COLOR.get(value, "lightgray")))
                )
                painter.setPen(Qt.NoPen)
                painter.drawRoundedRect(rect, 3, 3)
                painter.setPen(QPen(QColor("white")))
                painter.drawText(rect, Qt.AlignCenter | Qt.AlignVCenter, value)
                x += width + 20

            return {"pixmap": pix}

        return super().format(field, value, option, is_selected)

    # def paint(
    #     self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex
    # ):
    #     """Apply graphical formatting to each item in each displayed column in the view"""
    #     brush = QBrush()
    #     pen = QPen()
    #     font = QFont()

    #     if option.state & QStyle.State_Selected:
    #         text_color = option.palette.color(QPalette.Normal, QPalette.BrightText)
    #     else:
    #         text_color = option.palette.color(QPalette.Normal, QPalette.Text)

    #     is_selected = option.state & QStyle.State_Selected

    #     # Default theme color
    #     pen.setColor(text_color)

    #     field_name = self.field_name(index).lower()
    #     value = self.value(index)
