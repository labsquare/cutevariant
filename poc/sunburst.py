from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWidgets import *


import sys

from math import sin, cos, radians, atan2, sqrt, degrees


def lerp(p1: QPoint, p2: QPoint, alpha: float):
    return p1 * alpha + p2 * (1 - alpha)


def in_interval(x, a, b):
    return x >= a and x < b


class SunburstWidget(QWidget):
    """
    Example json file:
    {
        "label" : "all",
        "part" : 1,
        "subparts" :
        [
            {
                "label" : "HIGH"
                "part" : 0.7,
                "suparts" :
                [
                    {
                        "label" : "not so HIGH",
                        "part" : 0.4
                    },
                    {
                        "label" : "mildly HIGH",
                        "part" : 0.2
                    },
                    {
                        "label" : "somehow HIGH",
                        "part" : 0.1
                    },
                    {
                        "label" : "pretty HIGH",
                        "part" : 0.3
                    }
                ]
            },
            {
                "label" : "LOW",
                "part" : 0.3,
                "subparts" :
                [
                    {
                        "label" : "kinda LOW",
                        "part" : 0.4
                    },
                    {
                        "label" : "really LOW",
                        "part" : 0.6
                    }
                ]
            }
        ]
    }
    Out of this kind of json input, it shows each layer of the graph in a different color
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._data = None
        self.mouse_pos = None
        self._mouse_zone = [
            0,
            0,
        ]  # A list of angular position (radius,angle) of the mouse in the diagram coordinates
        self.setMouseTracking(True)
        self.painter_paths = []

        self.build_chart()

    def set_data(self, data: dict):
        self._data = data
        self.update()
        self.arc_paths = []

    def build_chart(self):

        side = min(self.rect().width(), self.rect().height())

        area = QRect(0, 0, side, side)
        area.moveCenter(self.rect().center())

        r1 = side / 2
        r2 = r1 + side / 4

        start_angle = 0
        for angle in [0.5, 0.4, 0.1]:

            painter_path = SunburstWidget.create_arc_path(
                area, r1, r2, start_angle, angle * 360
            )

            self.painter_paths.append(painter_path)

            start_angle += angle * 360

    def paintEvent(self, event: QPaintEvent):

        painter = QPainter()
        painter.begin(self)

        painter.setRenderHint(QPainter.Antialiasing)
        brush = QBrush()

        for i, path in enumerate(self.painter_paths):
            painter.drawPath(path)
            painter.fillPath(path, QColor(i * 100, 255, 255))

        # sat = 100

        # color = QColor.fromHsv((start_angle * 4) % 100, sat, 255)

        # # sat = 100
        # # if in_interval(self._mouse_zone[1], start_angle, start_angle + 360 * angle):
        # #     sat = 255
        # # color = QColor.fromHsv((start_angle * 4) % 100, sat, 255)

        # start_angle += angle * 360

        # painter.fillPath(painter_path, color)
        # painter.end()

    def mouseMoveEvent(self, event: QMouseEvent):

        self.mouse_pos = event.pos()

        for path in self.painter_paths:

            if path.contains(self.mouse_pos):

                # Changer la couleur dans les datas
                self.update()

        # x, y = event.localPos().x(), event.localPos().y()
        # xc = self.geometry().width() / 2
        # yc = self.geometry().height() / 2
        # self._mouse_zone[0] = sqrt((x - xc) ** 2 + (y - yc) ** 2)
        # self._mouse_zone[1] = degrees(atan2(y - yc, xc - x)) + 180
        self.update()

    def create_arc_path(
        rect: QRect,
        inner_radius: int,
        outer_radius: int,
        start_angle: float,
        span_angle: float,
    ) -> QPainterPath:
        center = rect.center()

        inner_rect = QRect(0, 0, inner_radius, inner_radius)
        inner_rect.moveCenter(center)

        outer_rect = QRect(0, 0, outer_radius, outer_radius)
        outer_rect.moveCenter(center)

        painter_path = QPainterPath(rect.center())

        painter_path.arcMoveTo(inner_rect, start_angle)
        start_point = painter_path.currentPosition()

        painter_path.arcTo(outer_rect, start_angle, span_angle)
        painter_path.lineTo(
            lerp(painter_path.currentPosition(), center, inner_radius / outer_radius)
        )
        painter_path.arcTo(inner_rect, start_angle + span_angle, -span_angle)

        return painter_path


def main(argv):
    app = QApplication(argv)
    window = SunburstWidget()
    window.show()
    return app.exec_()


if __name__ == "__main__":
    exit(main(sys.argv))
