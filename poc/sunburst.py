from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWidgets import *


import sys

from math import sin,cos,radians,atan2,sqrt,degrees

def lerp(p1:QPoint,p2:QPoint,alpha:float):
    return p1*alpha + p2*(1-alpha)

def in_interval(x,a,b):
    return x>=a and x<b


def draw_doughnut_part(rect:QRect,r1:int,r2:int,start_angle:float,span_angle:float):
    c=rect.center()
    inner_rect = QRect(c-QPoint(r1/2,r1/2),QSize(r1,r1))
    outer_rect = QRect(c-QPoint(r2/2,r2/2),QSize(r2,r2))

    painter_path=QPainterPath(rect.center())

    painter_path.arcMoveTo(inner_rect,start_angle)
    start_point = painter_path.currentPosition()
    
    painter_path.arcTo(outer_rect,start_angle,span_angle)
    painter_path.lineTo(lerp(painter_path.currentPosition(),c,r1/r2))
    painter_path.arcTo(inner_rect,start_angle+span_angle,-span_angle)

    return painter_path

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
    def __init__(self,parent=None):
        super().__init__(parent)
        self._data = None
        self._mouse_zone = [0,0] # A list of angular position (radius,angle) of the mouse in the diagram coordinates
        self.setMouseTracking(True)

    def set_data(self,data: dict):
        self._data = data
        self.update()

    def paintEvent(self,event: QPaintEvent):
        side = min(event.rect().width(),event.rect().height())
        topleft = QPoint((event.rect().width()-side)/2,(event.rect().height()-side)/2)
        area = QRect(topleft,QSize(side,side))

        r1 = side/2
        r2 = r1 + side/4

        start_angle = 0
        for angle in [0.5,0.4,0.1]:

            painter_path = draw_doughnut_part(area,r1,r2,start_angle,angle*360)

            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            brush = QBrush()

            sat = 100
            if in_interval(self._mouse_zone[1],start_angle,start_angle+360*angle):
                sat = 255
            color = QColor.fromHsv((start_angle*4)%100,sat,255)

            start_angle += angle * 360

            painter.fillPath(painter_path,color)
            painter.end()

            

    def mouseMoveEvent(self,event:QMouseEvent):
        x,y = event.localPos().x(),event.localPos().y()
        xc = self.geometry().width()/2
        yc = self.geometry().height()/2
        self._mouse_zone[0] = sqrt((x-xc)**2+(y-yc)**2)
        self._mouse_zone[1] = degrees(atan2(y-yc,xc-x))+180
        self.update()
        

def main(argv):
    app = QApplication(argv)
    window = SunburstWidget()
    window.show()
    return app.exec_()

if __name__ == "__main__":
    exit(main(sys.argv))