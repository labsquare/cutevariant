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
from cutevariant import LOGGER

from cutevariant.gui.widgets import VqlSyntaxHighlighter
from cutevariant.config import Config


# def sql_to_vector_converter(data):
#     return [int(i) for i in str(data, encoding="utf8").split(",") if i.isnumeric()]


# def list_to_sql_adapter(data: list):
#     return ",".join([d for d in data if d])


# # This registration of types in sqlite3 is so important it must be set in this module before anything else
# sqlite3.register_converter("VECTOR", sql_to_vector_converter)
# sqlite3.register_adapter(list, list_to_sql_adapter)

# Forget about vectors. Converting from/to list in python is really straightforward


def overlap(interval1: list, interval2: list) -> typing.Tuple[bool, int, int]:
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

    def load(self, data: dict):
        """From sqlite dict"""
        self.cds_start = data["cds_start"]
        self.cds_end = data["cds_end"]
        self.exon_starts = [int(i) for i in data["exon_starts"].split(",")]
        self.exon_ends = [int(i) for i in data["exon_ends"].split(",")]
        self.tx_start = data["tx_start"]
        self.tx_end = data["tx_end"]
        self.transcript_name = data["transcript_name"]

        self.exon_count = len(self.exon_starts) if self.exon_starts else 0


class GeneView(QAbstractScrollArea):
    """A class to visualize variants on a gene diagram, showing introns, exons, and coding sequence."""

    MOUSE_SELECT_MODE = 0  # Mouse clicking and dragging causes rectangle selection
    MOUSE_PAN_MODE = 1  # Mouse clicking and dragging causes view panning

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

        # self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.horizontalScrollBar().setRange(0, 0)
        self.horizontalScrollBar().valueChanged.connect(self.set_translation)

        self.resize(640, 200)
        # QScroller.grabGesture(self.viewport(), QScroller.LeftMouseButtonGesture)

        self.region = None
        color = self.palette().color(QPalette.Highlight)
        self.region_pen = QPen(color)
        color.setAlphaF(0.3)
        self.region_brush = QBrush(color)

        self.viewport().setMouseTracking(True)

        self.set_mouse_mode(GeneView.MOUSE_SELECT_MODE)
        self.cursor_selects = False

        self.selected_exon = None
        self._sample_count = 1

    def set_gene(self, gene: Gene):

        self.gene = gene
        self.viewport().update()

    def get_mouse_mode(self) -> int:
        """Return Mouse mode.

        Returns:
            int: GeneView.MOUSE_SELECT_MODE or GeneView.MOUSE_PAN_MODE
        """
        return self._mouse_mode

    def set_mouse_mode(self, mode: int):
        """Set Mouse mode

        Args:
            mode (int): GeneView.MOUSE_SELECT_MODE or GeneView.MOUSE_PAN_MODE

        Raises:
            ValueError: if wrong mode
        """
        if mode == GeneView.MOUSE_SELECT_MODE:
            self._mouse_mode = mode
            QScroller.ungrabGesture(self.viewport())
            self.setCursor(Qt.ArrowCursor)
        elif mode == GeneView.MOUSE_PAN_MODE:
            self._mouse_mode = mode
            QScroller.grabGesture(self.viewport(), QScroller.LeftMouseButtonGesture)
            self.setCursor(Qt.OpenHandCursor)
        else:
            raise ValueError(
                "Cannot set mouse mode to %s (accepted modes are MOUSE_PAN_MODE,MOUSE_SELECT_MODE",
                str(mode),
            )

    @property
    def cursor_selects(self) -> bool:
        return self._cursor_selects

    @cursor_selects.setter
    def cursor_selects(self, value: bool):
        self._cursor_selects = value

    def paintEvent(self, event: QPaintEvent):
        """override paintEvent

        Draw all things

        Args:
            event (QPaintEvent):

        """
        painter = QPainter()
        painter.begin(self.viewport())
        painter.setBrush(QBrush(self.palette().color(QPalette.Base)))
        # painter.drawRect(self.rect())

        # draw guide
        self.area = self.area_rect()
        # painter.drawRect(self.area.adjusted(-2, -2, 2, 2))
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
        """Draw introns

        Args:
            painter (QPainter): Description
        """
        intron_rect = QRect(self.area)
        intron_rect.setHeight(self.intron_height)
        intron_rect.moveCenter(QPoint(self.area.center().x(), self.area.center().y()))
        linearGrad = QLinearGradient(QPoint(0, intron_rect.top()), QPoint(0, intron_rect.bottom()))

        color = self.palette().color(QPalette.Light)

        linearGrad.setColorAt(0, color)
        linearGrad.setColorAt(1, color.darker())
        brush = QBrush(linearGrad)
        painter.setBrush(brush)
        painter.drawRect(intron_rect)

    def _draw_variants(self, painter: QPainter):
        """Draw variants

        Args:
            painter (QPainter)
        """
        if self.variants:
            painter.save()
            for variant in self.variants:

                pos = variant[0]
                selected = variant[1]
                af = variant[2]

                LOLIPOP_HEIGH = 100
                y = self.rect().center().y() - LOLIPOP_HEIGH * af - 10

                pos = self._dna_to_pixel(pos)
                pos = self._pixel_to_scroll(pos)

                col_line = self.palette().color(QPalette.Text)
                col_line.setAlphaF(0.6)
                painter.setPen(col_line)
                painter.drawLine(pos, self.rect().center().y(), pos, y)

                rect = QRect(0, 0, 10, 10)
                painter.setPen(self.palette().color(QPalette.Window))
                painter.setBrush(self.palette().color(QPalette.Highlight))

                col = self.palette().color(QPalette.Text)
                if selected:
                    col = QColor("red")

                col.setAlphaF(0.6)
                rect.moveCenter(QPoint(pos, y))
                painter.setBrush(QBrush(col))
                painter.drawEllipse(rect)

            painter.restore()

    def _draw_exons(self, painter: QPainter):
        """Draw exons

        Args:
            painter (QPainter)
        """
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
                    start,
                    self.area.center().y() - self.exon_height / 2,
                )

                painter.drawRect(exon_rect)
                color = self.palette().color(QPalette.Highlight)

                linearGrad = QLinearGradient(
                    QPoint(0, exon_rect.top()), QPoint(0, exon_rect.bottom())
                )
                linearGrad.setColorAt(0, color)
                linearGrad.setColorAt(1, color.darker())
                brush = QBrush(linearGrad)
                painter.setBrush(brush)
                painter.drawRect(exon_rect)
            painter.restore()

    def _draw_exon_handles(self, painter: QPainter):
        """deprecated

        draw exon selector

        Args:
            painter (QPainter): Description
        """
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

                pen = QPen(self.palette().color(QPalette.Text))
                pen.setWidth(2)
                painter.setPen(pen)
                painter.drawEllipse(rect)
                font = QFont()
                font.setBold(True)
                painter.setFont(font)
                painter.drawLine(
                    QPoint(rect.center().x(), rect.top()),
                    QPoint(rect.center().x(), self.area_rect().center().y()),
                )

                painter.drawText(rect, Qt.AlignCenter, str(index))

            if self.selected_exon != None:
                self.setCursor(Qt.PointingHandCursor)
            else:
                # Wired.. .TODO refactor
                pass

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
        """Draw Coding Domain sequence

        Args:
            painter (QPainter)
        """
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
                    start,
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
        """Draw region rect

        Args:
            painter (QPainter): Description
        """
        if self.region:
            painter.save()
            painter.setBrush(self.region_brush)
            painter.setPen(self.region_pen)
            painter.drawRect(self.region)
            painter.restore()

    def area_rect(self) -> QRect:
        """Return drawing area rect

        Returns:
            QRect
        """
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
        scale = self.area_rect().width() / tx_size
        return dna * scale

    def _dna_to_scroll(self, dna: int) -> int:
        """Return scroll coordinate to dna coordinaite
        Args:
            dna (int)

        Returns:
            int: Coordinate in scroll area
        """
        return self._pixel_to_scroll(self._dna_to_pixel(dna))

    def _scroll_to_dna(self, pixel: int) -> int:
        """Return DNA coordinate from scroll coordinate

        Args:
            pixel (int)

        Returns:
            int:
        """
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
        max_scroll = (self.area_rect().width() * self.scale_factor) - self.area_rect().width()

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

    def zoom_to_exon(self, exon_id: int):

        if exon_id < self.gene.exon_count:

            start = self.gene.exon_starts[exon_id]
            end = self.gene.exon_ends[exon_id]

            self.zoom_to_region(start, end)

    def zoom_to_region(self, start: int, end: int):
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
        """Override

        Args:
            event (QKeyEvent)
        """
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

    def event(self, event: QEvent) -> bool:
        """Override

        Args:
            event (QEvent): Description

        Returns:
            TYPE: Description
        """
        # Change cursor when gesture in panning ...
        if event.type() == QEvent.Gesture:
            for g in event.gestures():
                if g.state() == Qt.GestureUpdated:
                    self.setCursor(Qt.ClosedHandCursor)
                else:
                    self.setCursor(Qt.OpenHandCursor)

        return super().event(event)

    def keyReleaseEvent(self, event: QKeyEvent):

        super().keyReleaseEvent(event)
        # self.setCursor(Qt.CrossCursor)
        # # Reset mouse mode to rect select (the default)
        # self.mouse_mode = MOUSE_SELECT_MODE
        # self.cursor_selects = False

    def mousePressEvent(self, event: QMouseEvent):
        """Override

        Args:
            event (QMouseEvent)
        """
        if self.selected_exon != None:
            self.zoom_to_region(
                self.gene.exon_starts[self.selected_exon],
                self.gene.exon_ends[self.selected_exon],
            )

        if self.get_mouse_mode() == GeneView.MOUSE_SELECT_MODE:

            if event.button() == Qt.LeftButton:
                self.region = QRect(0, 0, 0, 0)
                self.region.setHeight(self.viewport().height())
                self.region.setLeft(event.position().x())
                self.region.setRight(event.position().x())

            if event.button() == Qt.RightButton:
                self.reset_zoom()

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        """Override

        Args:
            event (QMouseEvent): Description
        """
        if self.region:
            self.region.setRight(event.position().x())

        # # Check if the mouse hovers an exon and, if so, selects it
        # if self.gene.tx_start and self.gene.tx_end:
        #     pass
        # else:
        #     self.selected_exon = -1

        self.viewport().update()

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        """Override

        Args:
            event (QMouseEvent)
        """
        if self.region:
            if self.region.normalized().width() < 5:
                self.region = None
                return

            self.region = self.region.normalized()

            if self.region.isEmpty():
                # There is no selection, dna_start - dna_end is too small, zooming will make no sense
                self.reset_zoom()
            else:
                dna_start = self._scroll_to_dna(self.region.left() - self.area_rect().left())

                dna_end = self._scroll_to_dna(self.region.right() - self.area_rect().left())

                print(self.region.width())
                self.zoom_to_region(dna_start, dna_end)
                self.region = None

        super().mouseReleaseEvent(event)

    def reset_zoom(self):
        """Resets viewer zoom."""
        if self.gene:
            self.zoom_to_region(self.gene.tx_start, self.gene.tx_end)
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
    REFRESH_ONLY_VISIBLE = True
    REFRESH_STATE_DATA = {"current_variant"}

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle(self.tr("Gene Viewer"))
        self.setWindowIcon(FIcon(0xF0684))

        self.view = GeneView()
        # annconn = sqlite3.connect(
        #     "/home/sacha/refGene.db", detect_types=sqlite3.PARSE_DECLTYPES
        # )
        # annconn.row_factory = sqlite3.Row

        # gene_data = dict(
        #     annconn.execute("SELECT * FROM annotations WHERE gene = 'GJB2'").fetchone()
        # )

        self.gene_name_combo = QComboBox()
        self.gene_name_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.gene_name_combo.setMaximumWidth(400)
        self.gene_name_combo.setEditable(True)
        self.gene_name_combo.lineEdit().setPlaceholderText("Gene name ...")

        self.transcript_name_combo = QComboBox()
        self.transcript_name_combo.setMaximumWidth(400)
        self.transcript_name_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.transcript_name_combo.setEditable(True)
        self.transcript_name_combo.lineEdit().setPlaceholderText("Transcript name ...")

        self.exon_combo = QComboBox()
        self.exon_combo.setMaximumWidth(400)

        self.toolbar = QToolBar()

        self.tool_widget = QWidget()
        hlayout = QHBoxLayout(self.tool_widget)
        hlayout.addWidget(self.gene_name_combo)
        hlayout.addWidget(self.transcript_name_combo)
        # hlayout.addWidget(self.exon_combo)
        hlayout.addStretch()
        self.toolbar.addWidget(self.tool_widget)

        # Empty widget
        self.empty_widget = QWidget()
        self.config_button = QLabel("Set a database from settings ... ")
        self.config_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        empty_layout = QVBoxLayout(self.empty_widget)
        empty_layout.setAlignment(Qt.AlignCenter)
        empty_layout.addWidget(self.config_button)

        self.stack_layout = QStackedLayout()
        self.stack_layout.addWidget(self.empty_widget)
        self.stack_layout.addWidget(self.view)

        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.toolbar)
        main_layout.addLayout(self.stack_layout)

        # Connect comboboxes to their respective callbacks
        self.exon_combo.activated.connect(
            lambda x: self.view.zoom_to_exon(self.exon_combo.currentData())
        )
        self.gene_name_combo.currentTextChanged.connect(self.on_selected_gene_changed)
        self.transcript_name_combo.currentTextChanged.connect(self.on_selected_transcript_changed)

        self.current_variant = {}

        self.selected_gene = ""
        self.selected_transcript = ""

        self.gene_names = []
        self.transcript_names = []

        self.gene_conn = None

    def on_open_project(self, conn):
        self.conn = conn
        try:
            self.load_config()
        except:
            LOGGER.debug("Cannot init gene viewer")

    def on_close_project(self):
        self.view.set_gene(None)

    def on_register(self, mainwindow: MainWindow):
        """ """
        pass

    def on_refresh(self):

        if not self.gene_conn:
            return

        """Called whenever this plugin needs updating."""
        self.current_variant = sql.get_variant(
            self.conn,
            self.mainwindow.get_state_data("current_variant")["id"],
            with_annotations=True,
        )

        # Config for gene_viewer
        config_gene_viewer = Config("gene_viewer")
        gene_field = config_gene_viewer.get("gene_field", "")
        transcript_field = config_gene_viewer.get("transcript_field", "")

        # Find gene from current variant, depending on the gene field in config
        gene = ""
        # gene from annotations
        if gene_field.split(".")[0] == "ann":
            if "annotations" in self.current_variant:
                if gene_field.split(".")[1] in self.current_variant["annotations"][0]:
                    gene = self.current_variant["annotations"][0][gene_field.split(".")[1]]
        # gene from common field
        else:
            if gene_field in self.current_variant:
                gene = self.current_variant[gene_field]

        # find transcript from current variant, depending on the transcript field in config
        transcript = ""
        # transcript from annotations
        if transcript_field.split(".")[0] == "ann":
            if "annotations" in self.current_variant:
                if transcript_field.split(".")[1] in self.current_variant["annotations"][0]:
                    transcript = self.current_variant["annotations"][0][
                        transcript_field.split(".")[1]
                    ].split(".")[0]
        # transcript from common field
        else:
            if transcript_field in self.current_variant:
                transcript = self.current_variant[transcript_field].split(".")[0]

        # set gene and transcript
        self.transcript_name_combo.blockSignals(True)
        self.gene_name_combo.setCurrentText(gene)
        self.transcript_name_combo.blockSignals(False)
        self.transcript_name_combo.setCurrentText(transcript)
        self.update_view()

    def load_config(self):
        config = Config("gene_viewer")
        db_path = config.get("db_path", "")

        if not os.path.exists(db_path):
            self.stack_layout.setCurrentIndex(0)
        else:
            self.stack_layout.setCurrentIndex(1)
            self.gene_conn = sqlite3.connect(db_path)
            self.gene_conn.row_factory = sqlite3.Row
            self.load_gene_names()
            self.load_transcript_names()

    def load_gene_names(self):
        """Called on startup by __init__, loads whole annotation table to populate gene names combobox"""

        if self.gene_conn:
            gene_names = [s["gene"] for s in self.gene_conn.execute("SELECT gene FROM genes")]
            self.gene_name_combo.clear()
            self.gene_name_combo.addItems(gene_names)

    def load_transcript_names(self):
        """Called whenever the selected gene changes. Allows the user to select the transcript of interest."""
        if self.gene_conn:
            transcript_names = (
                [
                    s["transcript_name"]
                    for s in self.gene_conn.execute(
                        f"SELECT transcript_name FROM genes WHERE gene = '{self.selected_gene}'"
                    )
                ]
                if self.selected_gene is not None
                else []
            )

            self.transcript_name_combo.clear()
            self.transcript_name_combo.addItems(transcript_names)
            if len(transcript_names) >= 1:
                # Select first transcript (by default)
                self.transcript_name_combo.setCurrentIndex(0)

    def load_exons(self):

        self.exon_combo.clear()
        if self.view.gene:
            for i in range(self.view.gene.exon_count):
                self.exon_combo.addItem(f"Exon {i+1}", i)

    # def on_selected_variant_changed(self):
    #     """Called when another variant is selected in the variant view"""
    #     self.current_variant = sql.get_one_variant(
    #         self.conn,
    #         self.mainwindow.get_state_data("current_variant")["id"],
    #         with_annotations=True,
    #     )

    #     self.selected_gene = self.current_variant["annotations"][0]["gene"]

    #     self.gene_name_combo.setCurrentText(self.selected_gene)

    def on_selected_gene_changed(self):
        """When the selected gene changes, load known transcripts for this gene"""
        self.selected_gene = self.gene_name_combo.currentText()
        self.load_transcript_names()

    def on_selected_transcript_changed(self):
        self.update_view()

    def update_view(self):

        if not self.current_variant:
            return

        # Udpate gene view
        gene = self.gene_name_combo.currentText()
        transcript = self.transcript_name_combo.currentText()
        query = f"SELECT transcript_name,tx_start,tx_end,cds_start,cds_end,exon_starts,exon_ends,gene FROM genes WHERE gene = '{gene}' AND transcript_name='{transcript}'"
        result = self.gene_conn.execute(query).fetchone()

        # Config
        config_gene_viewer = Config("gene_viewer")
        gene_field = config_gene_viewer.get("gene_field", "")

        # Existing annotation fields
        list_of_fields = []
        for field in sql.get_fields(self.conn):
            # list fields from common fields
            if field["category"] == "variants":
                name = field["name"]
                list_of_fields.append(name)
            # list fields from annotations fields
            if field["category"] == "annotations":
                name = field["name"]
                list_of_fields.append(f"ann.{name}")

        # Filters on gene field
        filters = {}
        # field exists in project
        if gene_field in list_of_fields:
            filters = {"$and": [{f"""{gene_field}""": gene}]}
        # field DOES NOT exists in project
        else:
            LOGGER.warning("Gene fields %s not in project", gene_field)

        # Get all variants
        fields = ["pos"]
        source = self.mainwindow.get_state_data("source")

        variants = []

        for v in sql.get_variants(self.conn, fields, source, filters, limit=None):
            pos = v["pos"]
            selected = pos == self.current_variant["pos"]
            variants.append((pos, selected, 0.5))

        if result is not None:
            gene = Gene()
            self.view.variants = variants
            gene.load(dict(result))
            self.view.set_gene(gene)

        # self.load_exons()


# # TODO: What if the filters have an '$or' operator as a root ?

# filters = {"$and": ["ann.gene" : gene]}

# filters["$and"].append({"ann.gene": self.selected_gene})

#         # # With this part, should ensure that the transcript names are from the same annotations database as the one we are using
#         # if self.selected_transcript:
#         #     filters["$and"].append({"ann.transcript": self.selected_transcript})

#         # Get variant info

#         # Set limit to None ONLY because we added a filter on selected gene (how bad can it be ?)
#         # At most, we have
#         variants = list(
#             sql.get_variants(
#                 self.conn,
#                 fields,
#                 self.mainwindow.get_state_data("source"),
#                 filters,
#                 limit=None,
#             )
#         )

#         self.view.gene.variants = variants
#         self.view.set_sample_count(len(list((sql.get_samples(self.conn)))))


if __name__ == "__main__":

    pass

    import sys
    import sqlite3

    import os

    app = QApplication(sys.argv)

    conn = sqlite3.connect("/home/sacha/refGene.db", detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row

    gene_data = dict(conn.execute("SELECT * FROM genes WHERE gene = 'NOD2'").fetchone())

    print(gene_data)
    # print(gene_data)
    gene = Gene()
    gene.load(gene_data)

    print(gene.tx_start + 100)

    view = GeneView()
    view.set_gene(gene)
    view.variants = [(20766921, True, 0.5)]
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
