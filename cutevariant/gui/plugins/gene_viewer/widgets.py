# Standard imports
import typing
import glob
import json
import os
import gzip
import sys
import sqlite3
import copy

# Qt imports
from PySide6.QtCore import *
from PySide6.QtWidgets import *
from PySide6.QtGui import *
from PySide6.QtSql import *

# Custom imports
from cutevariant.gui import style, plugin, FIcon, MainWindow
from cutevariant.core.querybuilder import build_vql_query, build_sql_query

from cutevariant.core import sql

from cutevariant.gui.widgets import VqlSyntaxHighlighter


# def sql_to_vector_converter(data):
#     return [int(i) for i in str(data, encoding="utf8").split(",") if i.isnumeric()]


# def list_to_sql_adapter(data: list):
#     return ",".join([d for d in data if d])


# # This registration of types in sqlite3 is so important it must be set in this module before anything else
# sqlite3.register_converter("VECTOR", sql_to_vector_converter)
# sqlite3.register_adapter(list, list_to_sql_adapter)

# Forget about vectors. Converting from/to list in python is really straightforward


def overlap(interval1, interval2):
    """
    Given [0, 4] and [1, 10] returns (True,1, 4)
    Given [0,10] and [15,20] return (False,0,0)
    Thanks to https://stackoverflow.com/questions/2953967/built-in-function-for-computing-overlap-in-python
    for saving me time !
    """
    _overlaps = True
    if interval2[0] <= interval1[0] and interval1[0] <= interval2[1]:
        start = interval1[0]
    elif interval1[0] <= interval2[0] and interval2[0] <= interval1[1]:
        start = interval2[0]
    else:
        _overlaps = False
        start, end = 0, 0

    if interval2[0] <= interval1[1] <= interval2[1]:
        end = interval1[1]
    elif interval1[0] <= interval2[1] <= interval1[1]:
        end = interval2[1]
    else:
        _overlaps = False
        start, end = 0, 0

    return (_overlaps, start, end)


def annotation_to_sqlite(ref_filename: str, db_filename: str):

    # Create databases
    conn = sqlite3.connect(db_filename)

    if not os.path.isfile(ref_filename):
        raise FileNotFoundError("%s : No such file or directory !")

    # Get only the base name (without extension) to give the database a name
    database_name = os.path.basename(ref_filename).split(".")[0]

    conn.execute(
        f"""
        CREATE TABLE {database_name}(  
        id INTEGER PRIMARY KEY,
        transcript_name TEXT, 
        tx_start INTEGER, 
        tx_end INTEGER,
        cds_start INTEGER,
        cds_end INTEGER,
        exon_starts TEXT,
        exon_ends TEXT,
        gene TEXT
        )

    """
    )

    data = []
    with gzip.open(ref_filename, "rb") as file:
        for index, line in enumerate(file):
            if line:
                line = line.decode("utf-8").strip().split("\t")

                transcript = line[1]
                txStart = line[4]
                txEnd = line[5]
                cdsStart = line[6]
                cdsEnd = line[7]
                exonStarts = line[9]
                exonEnds = line[10]
                gene = line[12]

                data.append(
                    (
                        None,
                        transcript,
                        txStart,
                        txEnd,
                        cdsStart,
                        cdsEnd,
                        exonStarts,
                        exonEnds,
                        gene,
                    )
                )

    conn.executemany(f"INSERT INTO {database_name} VALUES(?,?,?,?,?,?,?,?,?);", data)
    conn.commit()


# Each variant will have a color index to set a representation color
# Below is the definition of color mapping for these lollipops
VARIANT_LOLLIPOP_COLOR_MAP = {
    0: QColor("#FF0000"),
    1: QColor("#00FF00"),
    2: QColor("#0000FF"),
}

# These come from the Cute formatter
SO_COLOR = {
    # https://natsukis.livejournal.com/2048.html
    "missense_variant": "#bb96ff",
    "synonymous_variant": "#67eebd",
    "stop_gained": "#ed6d79",
    "stop_lost": "#ed6d79",
    "frameshift_variant": "#ff89b5",
    "upstream_gene_variant": "#ff80bb",
    "intron_variant": "#ffbb88",
    "downstream_gene_variant": "#bb55ff",
}


class Gene:
    """Class to hold a representation of a gene, with structural data and variant annotations.
    Structural data include coding sequence (start, end), exon list (starts, ends), exon count and variants found on the gene.
    """

    def __init__(self):
        self.cds_start = None
        self.cds_end = None
        self.exon_starts = None
        self.exon_ends = None
        self.tx_start = None
        self.tx_end = None
        self.transcript_name = None
        self.exon_count = 0
        self.variants = []

    def from_dict(self, data: dict):
        """From sqlite dict"""

        self.cds_start = data["cds_start"]
        self.cds_end = data["cds_end"]
        self.exon_starts = [int(i) for i in data["exon_starts"].split(",")]
        self.exon_ends = [int(i) for i in data["exon_ends"].split(",")]
        self.tx_start = data["tx_start"]
        self.tx_end = data["tx_end"]
        self.transcript_name = data["transcript_name"]

        self.exon_count = len(self.exon_starts) if self.exon_starts else 0


class DefaultLollipopDrawer:
    IMPACT_COLOR = {
        "HIGH": QColor("#ff4b5c"),
        "LOW": QColor("#056674"),
        "MODERATE": QColor("#ecad7d"),
        "MODIFIER": QColor("#ecad7d"),
    }

    @staticmethod
    def draw_variant(
        variant: dict,
        painter: QPainter,
        x: int,
        y_mark: int,
        y_base: int,
        sample_count=1,
        selected=False,
    ) -> None:

        color = DefaultLollipopDrawer.IMPACT_COLOR.get(
            variant.get("ann.impact"), QColor("#000000")
        )

        # Make the lollipop appear as big as the frequence of the variant in the studied samples
        # If sample count is wrong... TODO: make sure that the below division is always between 0 and 1...
        thickness = (
            (variant["count_var"] / sample_count) * 20 + 10 if sample_count else 10
        )
        if selected:
            thickness += 5
            y_mark -= 30
        pen = QPen(color)
        pen.setCapStyle(Qt.RoundCap)
        pen.setWidth(thickness)
        painter.setPen(pen)
        mark = QPoint(x, y_mark)
        base = QPoint(x, y_base)

        painter.drawPoint(mark)

        pen.setWidth(1)
        painter.setPen(pen)
        painter.drawLine(mark, base)

    @staticmethod
    def get_caption():
        """Returns a list of dicts, mapping a color or a size with its actual meaning on the graph
        Example return value:
            [
            {"color": QColor("#ff4b5c"), "text": "HIGH impact"},
            {"color": QColor("#ecad7d"), "text": "MODERATE impact"},
            {"color": QColor("#056674"), "text": "LOW impact"},
            {"color": QColor("#ecad7d"), "text": "MODIFIER impact"},
            {"size": 10, "text": "Really unfrequent variant"},
            {"size": 20, "text": "Half frequent variant"},
            {"size": 30, "text": "Most frequent variant"},
        ]
        """
        return [
            {"color": QColor("#ff4b5c"), "text": "HIGH impact"},
            {"color": QColor("#ecad7d"), "text": "MODERATE impact"},
            {"color": QColor("#056674"), "text": "LOW impact"},
            {"color": QColor("#ecad7d"), "text": "MODIFIER impact"},
            {"size": 10, "text": "Really unfrequent variant"},
            {"size": 20, "text": "Half frequent variant"},
            {"size": 30, "text": "Most frequent variant"},
        ]


# Defines available mouse modes:
MOUSE_SELECT_MODE = 0  # Mouse clicking and dragging causes rectangle selection
MOUSE_PAN_MODE = 1  # Mouse clicking and dragging causes view panning


class GeneView(QAbstractScrollArea):
    """A class to visualize variants on a gene diagram, showing introns, exons, and coding sequence."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.variants = [(20761708, "red", 0.9), (20761808, "red", 0.2)]

        self.gene = None

        # style
        self.cds_height = 40
        self.exon_height = 30
        self.intron_height = 20

        # self.showMaximized()

        self.scale_factor = 1
        self.translation = 0

        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.horizontalScrollBar().setRange(0, 0)

        self.horizontalScrollBar().valueChanged.connect(self.set_translation)

        self.resize(640, 200)
        # QScroller.grabGesture(self.viewport(), QScroller.LeftMouseButtonGesture)

        self.region = None

        self.region_brush = QBrush(QColor("#5094CB80"))
        # self.region_brush.setStyle(Qt.Dense4Pattern)
        self.region_pen = QPen(QColor("#1E3252"))

        self.viewport().setMouseTracking(True)

        self.mouse_mode = MOUSE_SELECT_MODE
        self.cursor_selects = False

        self.selected_exon = None
        self._sample_count = 1

        # This class holds only static methods
        self.lollipop_drawer = DefaultLollipopDrawer

    @property
    def mouse_mode(self) -> int:
        return self._mouse_mode

    @mouse_mode.setter
    def mouse_mode(self, value: int):

        if value == MOUSE_SELECT_MODE:
            self._mouse_mode = value
            QScroller.ungrabGesture(self.viewport())
            self.setCursor(Qt.ArrowCursor)
        elif value == MOUSE_PAN_MODE:
            self._mouse_mode = value
            QScroller.grabGesture(self.viewport(), QScroller.LeftMouseButtonGesture)
            self.setCursor(Qt.OpenHandCursor)
        else:
            raise ValueError(
                "Cannot set mouse mode to %s (accepted values are MOUSE_PAN_MODE,MOUSE_SELECT_MODE",
                str(value),
            )

    @property
    def cursor_selects(self) -> bool:
        return self._cursor_selects

    @cursor_selects.setter
    def cursor_selects(self, value: bool):
        self._cursor_selects = value

    def paintEvent(self, event: QPaintEvent):

        painter = QPainter()
        painter.begin(self.viewport())
        painter.setBrush(QBrush(QColor("white")))
        painter.drawRect(self.rect())

        # draw guide
        self.area = self.draw_area()
        painter.drawRect(self.area.adjusted(-2, -2, 2, 2))
        painter.setClipRect(self.area)

        if not self.gene:
            return

        if not (self.gene.tx_start and self.gene.tx_end):
            painter.drawText(
                self.area,
                Qt.AlignCenter,
                self.tr("No gene selected. Please chose one in the combobox"),
            )
            painter.end()
            return

        # self.marks = []

        # Draw variants
        self._draw_variants(painter)

        # Draw lollipops to highlight exon selection
        # self._draw_exon_handles(painter)

        # Draw intron Background
        self._draw_introns(painter)

        # Draw exons
        self._draw_exons(painter)

        # Draw CDS
        self._draw_cds(painter)

        # Draw rect selection region
        self._draw_region(painter)

        # Draw cursor line
        # if self.mouse_mode == MOUSE_SELECT_MODE:
        #     line_x = self.mapFromGlobal(QCursor.pos()).x()
        #     painter.drawLine(line_x, 0, line_x, self.rect().height())

        painter.end()

    def _draw_introns(self, painter: QPainter):
        intron_rect = QRect(self.area)
        intron_rect.setHeight(self.intron_height)
        intron_rect.moveCenter(QPoint(self.area.center().x(), self.area.center().y()))
        linearGrad = QLinearGradient(
            QPoint(0, intron_rect.top()), QPoint(0, intron_rect.bottom())
        )
        linearGrad.setColorAt(0, QColor("#FDFD97"))
        linearGrad.setColorAt(1, QColor("#FDFD97").darker())
        brush = QBrush(linearGrad)
        painter.setBrush(brush)
        painter.drawRect(intron_rect)

    def _draw_caption_color_block(
        self, painter: QPainter, color: QColor, text: str, pos: QPoint
    ) -> typing.Tuple[int, int]:
        """Draws a caption color block at position pos, using painter.

        Args:
            painter (QPainter): painter to draw with
            color (QColor): color of the caption
            text (str): caption's description
            pos (QPoint): UpperLeft corner to draw this block at

        Returns:
            typing.Tuple[int,int]: Returns (width,height) of the block that was drawn
        """
        painter.save()

        font_metrics = QFontMetrics(self.font())

        # Draw color rectangle
        painter.setBrush(QBrush(color))
        painter.setPen(QPen(Qt.NoPen))
        color_rect = QRect(pos, QSize(15, 15))
        painter.drawRect(color_rect)

        # Draw caption text
        painter.setBrush(self.palette().color(QPalette.Base))
        painter.setPen(QPen(QColor("grey")))
        painter.drawText(color_rect.right(), pos.y() + 15, text)

        text_bounding_rect = font_metrics.boundingRect(text)

        w = color_rect.width() + text_bounding_rect.width()
        h = max(color_rect.height(), text_bounding_rect.height())

        painter.restore()

        return w, h

    def _draw_caption_circle_block(
        self, painter: QPainter, size: int, text: str, pos: QPoint
    ) -> typing.Tuple[int, int]:
        """Draws a caption size hint block at position pos, using painter.

        Args:
            painter (QPainter): painter to draw with
            color (QColor): color of the caption
            text (str): caption's description
            pos (QPoint): UpperLeft corner to draw this block at

        Returns:
            typing.Tuple[int,int]: Returns (width,height) of the block that was drawn
        """
        painter.save()

        font_metrics = QFontMetrics(self.font())

        # Draw head circle
        painter.setBrush(QBrush(QColor("grey")))
        painter.setPen(QPen(Qt.NoPen))
        size_hint_head = QRect(pos + QPoint(0, 10), QSize(size / 2, size / 2))
        painter.drawEllipse(size_hint_head)

        # Draw caption
        painter.setBrush(self.palette().color(QPalette.Base))
        painter.setPen(QPen(QColor("grey")))
        painter.drawText(size_hint_head.right() + 10, pos.y() + 15, text)

        text_bounding_rect = font_metrics.boundingRect(text)

        w = size_hint_head.width() + text_bounding_rect.width()
        h = max(size_hint_head.height(), text_bounding_rect.height())

        painter.restore()

        return w, h

    def _draw_caption(self, painter: QPainter):
        """Draws caption to explain shape and color of lollipop graph

        Args:
            painter (QPainter): painter reference to draw on its device
        """
        caption = self.lollipop_drawer.get_caption()

        x, y = self.area.topLeft().toTuple()
        col_width = 0
        for idx, item in enumerate(caption):
            if "color" in item:
                w, h = self._draw_caption_color_block(
                    painter, item["color"], item["text"], QPoint(x, y)
                )
                col_width = max(col_width, w)
                y += h

        x += col_width + 5
        y = self.area.top()

        for idx, item in enumerate(caption):
            if "size" in item:
                w, h = self._draw_caption_circle_block(
                    painter, item["size"], item["text"], QPoint(x, y)
                )
                col_width = max(col_width, w)
                y += h

    def _draw_variants(self, painter: QPainter):
        if self.variants:
            painter.save()
            for variant in self.variants:

                pos = variant[0]
                col = variant[1]
                af = variant[2]

                LOLIPOP_HEIGH = 100
                y = self.rect().center().y() - LOLIPOP_HEIGH * af - 10

                pos = self._dna_to_scroll(pos)

                painter.setPen(self.palette().color(QPalette.Window))
                painter.drawLine(pos, self.rect().center().y(), pos, y)

                rect = QRect(0, 0, 10, 10)
                painter.setPen(self.palette().color(QPalette.Window))
                painter.setBrush(self.palette().color(QPalette.Highlight))

                rect.moveCenter(QPoint(pos, y))
                painter.drawEllipse(rect)

            painter.restore()

    def _draw_exons(self, painter: QPainter):

        if self.gene.exon_count:
            painter.save()
            painter.setClipRect(self.area)

            for i in range(self.gene.exon_count):

                start = self._dna_to_pixel(self.gene.exon_starts[i])
                end = self._dna_to_pixel(self.gene.exon_ends[i])

                start = self._pixel_to_scroll(start)
                end = self._pixel_to_scroll(end)

                # for m in self.marks:
                #     print("mark", m)
                #     painter.drawLine(m, 0, m, self.area.bottom())

                # draw exons
                exon_rect = QRect(0, 0, end - start, self.exon_height)
                exon_rect.moveTo(
                    start + self.area.left(),
                    self.area.center().y() - self.exon_height / 2,
                )

                painter.drawRect(exon_rect)

                linearGrad = QLinearGradient(
                    QPoint(0, exon_rect.top()), QPoint(0, exon_rect.bottom())
                )
                linearGrad.setColorAt(0, QColor("#789FCC"))
                linearGrad.setColorAt(1, QColor("#789FCC").darker())
                brush = QBrush(linearGrad)
                painter.setBrush(brush)
                painter.drawRect(exon_rect)
            painter.restore()

    def _draw_exon_handles(self, painter: QPainter):
        if self.gene.exon_count:
            painter.save()
            painter.setClipRect(self.area)
            painter.setRenderHint(QPainter.Antialiasing)

            # Schedule rects for drawing, so we know wich one was selected before drawing it on top
            rects_to_draw = []
            mouse_hovered_handle = False
            self.selected_exon = None

            for i in range(self.gene.exon_count):

                start = self._dna_to_scroll(self.gene.exon_starts[i])
                end = self._dna_to_scroll(self.gene.exon_ends[i])

                base = (end + start) / 2

                head_width = 34
                head_height = self.exon_height

                head_rect = QRect(0, 0, head_width, head_height)

                head_rect.moveCenter(
                    QPoint(
                        base + self.area.left(),
                        self.area.center().y() + self.cds_height + 15,
                    )
                )

                # If the head rect is outside the boundaries, do nothing
                if self.area.intersected(head_rect) != head_rect:
                    continue

                # Now that the head rect is at its definitive place, let's check if the cursor hovers it (Thanks @dridk!)
                if head_rect.contains(self.mapFromGlobal(QCursor.pos())):
                    self.selected_exon = i
                    rects_to_draw.insert(0, (i, head_rect))

                else:
                    rects_to_draw.append((i, head_rect))

            for index, rect in rects_to_draw[::-1]:
                if index == self.selected_exon:
                    painter.setBrush(QBrush(self.palette().color(QPalette.Highlight)))

                else:
                    painter.setBrush(QBrush(self.palette().color(QPalette.Highlight)))

                pen = QPen(self.palette().color(QPalette.Text))
                pen.setWidth(2)
                painter.setPen(pen)
                painter.drawEllipse(rect)
                font = QFont()
                font.setBold(True)
                painter.setFont(font)
                painter.drawLine(
                    QPoint(rect.center().x(), rect.top()),
                    QPoint(rect.center().x(), self.draw_area().center().y()),
                )

                painter.drawText(rect, Qt.AlignCenter, str(index))

            if self.selected_exon != None:
                self.setCursor(Qt.PointingHandCursor)
            else:
                # Wired.. .TODO refactor
                self.mouse_mode = self.mouse_mode

            # selected_handle = None
            # for exon_index, handle in rects_to_draw:
            #     linearGrad = QLinearGradient(
            #         QPoint(0, handle.top()), QPoint(0, handle.bottom())
            #     )
            #     if exon_index == self.selected_exon:
            #         selected_handle = handle
            #         continue
            #     else:
            #         linearGrad.setColorAt(0, QColor("#789FCC"))
            #         linearGrad.setColorAt(1, QColor("#789FCC"))
            #     brush = QBrush(linearGrad)
            #     painter.setBrush(brush)
            #     painter.setPen(no_pen)
            #     painter.drawEllipse(handle)
            #     painter.setPen(white_pen)
            #     painter.drawText(handle, Qt.AlignCenter, str(exon_index))

            # # Always draw selected handle last, no matter what
            # if selected_handle:
            #     selected_handle.setWidth(selected_handle.width() * 1.2)
            #     selected_handle.setHeight(selected_handle.height() * 1.2)
            #     linearGrad = QLinearGradient(
            #         QPoint(0, selected_handle.top()),
            #         QPoint(0, selected_handle.bottom()),
            #     )
            #     linearGrad.setColorAt(0, QColor("#789FCC"))
            #     linearGrad.setColorAt(1, QColor("#789FCC").darker())
            #     brush = QBrush(linearGrad)
            #     painter.setBrush(brush)
            #     painter.setPen(no_pen)
            #     painter.drawEllipse(selected_handle)
            #     painter.drawPolygon(
            #         QPolygon(
            #             [
            #                 selected_handle.center() + QPoint(5, 0),
            #                 QPoint(
            #                     selected_handle.center().x(), self.area.height() / 2
            #                 ),
            #                 selected_handle.center() + QPoint(-5, 0),
            #             ]
            #         )
            #     )
            #     painter.setPen(white_pen)
            #     painter.drawText(
            #         selected_handle, Qt.AlignCenter, str(self.selected_exon)
            #     )

            painter.restore()

    def _draw_cds(self, painter: QPainter):
        painter.save()
        if self.gene.cds_start and self.gene.cds_end:
            painter.setClipRect(self.area)

            # We draw, on every exon, the CDS rectangle (if existing)
            for i in range(self.gene.exon_count):
                overlaps, start, end = overlap(
                    [self.gene.cds_start, self.gene.cds_end],
                    [self.gene.exon_starts[i], self.gene.exon_ends[i]],
                )

                # Don't draw CDS rectangle on this exon, there is none
                if not overlaps:
                    continue

                start = self._dna_to_pixel(start)
                end = self._dna_to_pixel(end)

                start = self._pixel_to_scroll(start)
                end = self._pixel_to_scroll(end)

                cds_rect = QRect(0, 0, end - start, self.cds_height)
                cds_rect.moveTo(
                    start + self.area.left(),
                    self.area.center().y() - self.cds_height / 2,
                )

                linearGrad = QLinearGradient(
                    QPoint(0, cds_rect.top()), QPoint(0, cds_rect.bottom())
                )
                linearGrad.setColorAt(0, QColor("#194980"))
                linearGrad.setColorAt(1, QColor("#194980").darker(400))
                brush = QBrush(linearGrad)
                painter.setBrush(brush)
                painter.drawRect(cds_rect)

        painter.restore()

    def _draw_region(self, painter: QPainter):
        if self.region:
            painter.save()
            painter.setBrush(self.region_brush)
            painter.setPen(self.region_pen)
            painter.drawRect(self.region)
            painter.restore()

    def draw_area(self):
        return self.viewport().rect().adjusted(10, 10, -10, -10)

    def _pixel_to_dna(self, pixel: int) -> int:
        """Convert pixel coordinate to dna

        Args:
            pixel (int): coordinate in pixel

        Returns:
            int: coordinate in dna
        """
        tx_size = self.gene.tx_end - self.gene.tx_start
        scale = tx_size / self.area.width()
        return pixel * scale + self.gene.tx_start

    def _dna_to_pixel(self, dna: int) -> int:
        """Convert dna coordinate to pixel

        Args:
            dna (int): coordinate in dna

        Returns:
            int: coordinate in pixel
        """

        # normalize dna
        dna = dna - self.gene.tx_start
        tx_size = self.gene.tx_end - self.gene.tx_start
        scale = self.area.width() / tx_size
        return dna * scale

    def _dna_to_scroll(self, dna: int) -> int:
        return self._pixel_to_scroll(self._dna_to_pixel(dna))

    def _scroll_to_dna(self, pixel: int) -> int:
        return self._pixel_to_dna(self._scroll_to_pixel(pixel))

    def _pixel_to_scroll(self, pixel: int) -> int:
        """Convert pixel coordinate to scroll area

        Args:
            pixel (int): Coordinate in pixel

        Returns:
            int: Return coordinate in scroll area
        """
        return pixel * self.scale_factor - self.translation

    def _scroll_to_pixel(self, pos: int) -> int:
        """Convert scroll coordinate to pixel

        Args:
            pos (int): Coordinate from scrollarea

        Returns:
            int: Coordinate in pixel
        """
        return (pos + self.translation) / self.scale_factor

    @Slot(int)
    def set_scale(self, x: int):
        """Set view scale.

        This method rescale the view . It makes possible to zoom in or zoom out

        Args:
            x (int): scale factor.
        """
        self.scale_factor = x

        min_scroll = 0
        max_scroll = (
            self.draw_area().width() * self.scale_factor
        ) - self.draw_area().width()

        previous = self.horizontalScrollBar().value()
        previous_max = self.horizontalScrollBar().maximum()

        self.horizontalScrollBar().setRange(min_scroll, max_scroll)

        if previous_max > 1:
            new = previous * self.horizontalScrollBar().maximum() / previous_max
        else:
            new = self.horizontalScrollBar().maximum() / 2

        self.horizontalScrollBar().setValue(new)

    def set_translation(self, x: int):
        """Set Translation

        This method translate the view.
        This method is called by scrollbar

        Args:
            x (int): translation factor between 0 and (transcript size in pixel * the scale factor)
        """
        self.translation = x
        self.viewport().update()

    def wheelEvent(self, event):
        """override

        Zoom in or zoom out with the mouse wheel

        """
        if event.delta() > 0:
            self.set_scale(self.scale_factor + 0.5)
        else:
            if self.scale_factor > 1:
                self.set_scale(self.scale_factor - 0.5)

    def zoom_to_dna_interval(self, start: int, end: int):
        """Sets the current view bounds to a rect around DNA sequence spanning from start to end

        Args:
            start (int): DNA start position in the current transcript
            end (int): DNA end position in the current transcript
        """
        dna_pixel_size = end - start

        tx_pixel_size = self.gene.tx_end - self.gene.tx_start
        scale = tx_pixel_size / dna_pixel_size
        self.set_scale(scale)
        self.horizontalScrollBar().setValue(self._dna_to_pixel(start) * scale)
        self.viewport().update()

    def keyPressEvent(self, event: QKeyEvent):
        # If any key is pressed, switch to mouse pan mode

        super().keyPressEvent(event)

        # if event.key() == Qt.Key_Control:
        #     self.setCursor(Qt.PointingHandCursor)
        #     self.cursor_selects = True
        #     self.mouse_mode = MOUSE_PAN_MODE

        # if event.key() == Qt.Key_Shift:
        #     self.setCursor(Qt.OpenHandCursor)
        #     self.cursor_selects = False
        #     self.mouse_mode = MOUSE_PAN_MODE

    def event(self, event):

        # Change cursor when gesture in panning ...
        if event.type() == QEvent.Gesture:
            for g in event.gestures():
                if g.state() == Qt.GestureUpdated:
                    self.setCursor(Qt.ClosedHandCursor)
                else:
                    self.setCursor(Qt.OpenHandCursor)

        super().event(event)

    def keyReleaseEvent(self, event: QKeyEvent):

        super().keyReleaseEvent(event)
        # self.setCursor(Qt.CrossCursor)
        # # Reset mouse mode to rect select (the default)
        # self.mouse_mode = MOUSE_SELECT_MODE
        # self.cursor_selects = False

    def mousePressEvent(self, event: QMouseEvent):

        if self.selected_exon != None:
            self.zoom_to_dna_interval(
                self.gene.exon_starts[self.selected_exon],
                self.gene.exon_ends[self.selected_exon],
            )

        if self.mouse_mode == MOUSE_SELECT_MODE:

            if event.button() == Qt.LeftButton:
                self.region = QRect(0, 0, 0, 0)
                self.region.setHeight(self.viewport().height())
                self.region.setLeft(event.pos().x())
                self.region.setRight(event.pos().x())

            if event.button() == Qt.RightButton:
                self.reset_zoom()

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):

        if self.region:
            self.region.setRight(event.pos().x())

        # # Check if the mouse hovers an exon and, if so, selects it
        # if self.gene.tx_start and self.gene.tx_end:
        #     pass
        # else:
        #     self.selected_exon = -1

        self.viewport().update()

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):

        if self.region:
            if self.region.normalized().width() < 5:
                self.region = None
                return

            self.region = self.region.normalized()

            if self.region.isEmpty():
                # There is no selection, dna_start - dna_end is too small, zooming will make no sense
                self.reset_zoom()
            else:
                dna_start = self._scroll_to_dna(
                    self.region.left() - self.draw_area().left()
                )

                dna_end = self._scroll_to_dna(
                    self.region.right() - self.draw_area().left()
                )

                print(self.region.width())
                self.zoom_to_dna_interval(dna_start, dna_end)
                self.region = None

        super().mouseReleaseEvent(event)

    def reset_zoom(self):
        """Resets viewer zoom."""
        if self.gene:
            self.zoom_to_dna_interval(self.gene.tx_start, self.gene.tx_end)
        else:
            self.set_scale(1)
            self.set_translation(0)

    def set_sample_count(self, value):
        self._sample_count = value

    def get_sample_count(self):
        return self._sample_count


class GeneViewerWidget(plugin.PluginWidget):
    """Widget to show user-selected gene with its associated variants in the project.
    The user can choose either gene/transcript or select a variant in the view. Both will make this
    widget display chosen gene with **selected** variants.
    """

    # LOCATION = plugin.FOOTER_LOCATION
    ENABLE = True
    REFRESH_ONLY_VISIBLE = False
    REFRESH_STATE_DATA = {"current_variant"}

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle(self.tr("Gene Viewer"))

        self.view = GeneView()

        annconn = sqlite3.connect(
            "/home/sacha/refGene.db", detect_types=sqlite3.PARSE_DECLTYPES
        )
        annconn.row_factory = sqlite3.Row

        gene_data = dict(
            annconn.execute("SELECT * FROM annotations WHERE gene = 'GJB2'").fetchone()
        )

        # print(gene_data)
        gene = Gene()
        gene.from_dict(gene_data)

        self.view.gene = gene

        self.gene_name_combo = QComboBox()
        self.gene_name_combo.setEditable(True)

        self.transcript_name_combo = QComboBox()
        self.transcript_name_combo.setEditable(True)

        self.toolbar = QToolBar()

        self.toolbar.addAction(
            FIcon(0xF1276), self.tr("Reset zoom"), lambda: self.view.reset_zoom()
        )

        # We need two comboboxes, one for the gene name, and one for one of its transcripts
        self.toolbar.addWidget(self.gene_name_combo)
        self.toolbar.addWidget(self.transcript_name_combo)

        self.vlayout = QVBoxLayout(self)
        self.vlayout.addWidget(self.toolbar)
        self.vlayout.addWidget(self.view)

        # Connect comboboxes to their respective callbacks
        # self.gene_name_combo.currentTextChanged.connect(self.on_selected_gene_changed)
        # self.transcript_name_combo.currentTextChanged.connect(
        #     self.on_selected_transcript_changed
        # )

        self.current_variant = {}

        self.selected_gene = ""
        self.selected_transcript = ""

        self.gene_names = []
        self.transcript_names = []

        # self.load_gene_names()

    def on_open_project(self, conn):
        self.conn = conn

    def on_register(self, mainwindow: MainWindow):
        """ """
        pass

    def on_refresh(self):
        """Called whenever this plugin needs updating."""
        self.current_variant = sql.get_one_variant(
            self.conn,
            self.mainwindow.get_state_data("current_variant")["id"],
            with_annotations=True,
        )

        self.selected_gene = self.current_variant["annotations"][0]["gene"]

        self.gene_name_combo.setCurrentText(self.selected_gene)

        self.update_shown_variants()


# def open_annotations_database(self):
#     """Initialize annotations database, i.e. open ensGene file and setup row factory"""
#     self.annotations_conn = sqlite3.connect(self.annotations_file_name)
#     self.annotations_conn.row_factory = sqlite3.Row

# def load_gene_names(self):
#     """Called on startup by __init__, loads whole annotation table to populate gene names combobox"""
#     self.gene_names = [
#         s["gene"] for s in self.annotations_conn.execute("SELECT gene FROM refGene")
#     ]
#     self.gene_name_combo.clear()
#     self.gene_name_combo.addItems(self.gene_names)

# def load_transcript_names(self):
#     """Called whenever the selected gene changes. Allows the user to select the transcript of interest."""
#     self.transcript_names = (
#         [
#             s["transcript_name"]
#             for s in self.annotations_conn.execute(
#                 f"SELECT transcript_name FROM refGene WHERE gene = '{self.selected_gene}'"
#             )
#         ]
#         if self.selected_gene is not None
#         else []
#     )

#     self.transcript_name_combo.clear()
#     self.transcript_name_combo.addItems(self.transcript_names)
#     if len(self.transcript_names) >= 1:
#         # Select first transcript (by default)
#         self.transcript_name_combo.setCurrentIndex(0)

# def on_selected_variant_changed(self):
#     """Called when another variant is selected in the variant view"""
#     self.current_variant = sql.get_one_variant(
#         self.conn,
#         self.mainwindow.get_state_data("current_variant")["id"],
#         with_annotations=True,
#     )

#     self.selected_gene = self.current_variant["annotations"][0]["gene"]

#     self.gene_name_combo.setCurrentText(self.selected_gene)

# def on_selected_gene_changed(self):
#     """When the selected gene changes, load known transcripts for this gene"""
#     self.selected_gene = self.gene_name_combo.currentText()
#     self.load_transcript_names()

# def on_selected_transcript_changed(self):
#     self.update_shown_variants()

# def update_shown_variants(self):
#     if self.selected_gene:
#         filters = copy.deepcopy(self.mainwindow.get_state_data("filters"))
#         self.selected_transcript = self.transcript_name_combo.currentText()

#         if self.selected_transcript:

#             fields = [
#                 "pos",  # So we can place the variant
#                 "ann.consequence",
#                 "ann.impact",
#                 "count_var",  # For the drawn size of this variant
#             ]

#             # TODO: What if the filters have an '$or' operator as a root ?
#             if "$and" not in filters:
#                 filters = {"$and": []}

#             filters["$and"].append({"ann.gene": self.selected_gene})

#             # # With this part, should ensure that the transcript names are from the same annotations database as the one we are using
#             # if self.selected_transcript:
#             #     filters["$and"].append({"ann.transcript": self.selected_transcript})

#             # Get variant info

#             # Set limit to None ONLY because we added a filter on selected gene (how bad can it be ?)
#             # At most, we have
#             variants = list(
#                 sql.get_variants(
#                     self.conn,
#                     fields,
#                     self.mainwindow.get_state_data("source"),
#                     filters,
#                     limit=None,
#                 )
#             )

#             self.view.gene.variants = variants
#             self.view.set_sample_count(len(list((sql.get_samples(self.conn)))))

#             query = self.annotations_conn.execute(
#                 f"SELECT transcript_name,tx_start,tx_end,cds_start,cds_end,exon_starts,exon_ends,gene FROM refGene WHERE gene = '{self.selected_gene}' AND transcript_name='{self.selected_transcript}'"
#             ).fetchone()

#             if query is None:
#                 print(
#                     "Cannot find gene",
#                     self.selected_gene,
#                     "and transcript",
#                     self.selected_transcript,
#                     sep=" ",
#                 )

#             else:
#                 gene_data = dict(query)
#                 self.view.gene.tx_start = gene_data["tx_start"]
#                 self.view.gene.tx_end = gene_data["tx_end"]
#                 self.view.gene.cds_start = gene_data["cds_start"]
#                 self.view.gene.cds_end = gene_data["cds_end"]
#                 self.view.gene.transcript_name = gene_data["transcript_name"]
#                 self.view.gene.exon_starts = [
#                     int(i)
#                     for i in gene_data["exon_starts"].split(",")
#                     if i.isnumeric()
#                 ]
#                 self.view.gene.exon_ends = [
#                     int(i)
#                     for i in gene_data["exon_ends"].split(",")
#                     if i.isnumeric()
#                 ]

#                 # # Set all attributes of our gene from the query
#                 # [
#                 #     setattr(self.view.gene, attr_name, gene_data[attr_name])
#                 #     for attr_name in gene_data
#                 #     if hasattr(self.view.gene, attr_name)
#                 # ]

#                 self.view.viewport().update()


if __name__ == "__main__":

    pass

    import sys
    import sqlite3

    import os

    app = QApplication(sys.argv)

    conn = sqlite3.connect(
        "/home/sacha/refGene.db", detect_types=sqlite3.PARSE_DECLTYPES
    )
    conn.row_factory = sqlite3.Row

    gene_data = dict(
        conn.execute("SELECT * FROM annotations WHERE gene = 'GJB2'").fetchone()
    )

    # print(gene_data)
    gene = Gene()
    gene.from_dict(gene_data)

    print(gene.tx_start + 100)

    view = GeneView()
    view.gene = gene
    view.show()
    view.resize(600, 500)

    # view.gene.exon_starts = [int(i) for i in gene_data["exon_starts"].split(",")]
    # view.gene.exon_ends = [int(i) for i in gene_data["exon_ends"].split(",")]

    # view.gene.exon_ends = gene_data["exon_ends"]
    # # Set all attributes of our gene from the query
    # [
    #     setattr(view.gene, attr_name, gene_data[attr_name])
    #     for attr_name in gene_data
    #     if hasattr(view.gene, attr_name)
    # ]

    # variants = [
    #     (view.gene.tx_start + 1000, 0),
    #     (view.gene.tx_start + 2000, 0),
    #     (view.gene.tx_start + 3000, 1),
    # ]

    # view.gene.variants = variants

    # view.viewport().update()

    app.exec()
