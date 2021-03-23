from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWidgets import *

import sys

from math import sin, cos, radians, atan2, sqrt, degrees

# Custom imports
import cutevariant.commons as cm

LOGGER = cm.logger()


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

    New example file (simpler)
    {
        "HIGH" :
        {
            "part" : 0.7,
            "subparts":
            [
                {"not so HIGH" : 0.4},
                {"mildly HIGH" : 0.2},
                {"somehow HIGH" : 0.1},
                {"pretty HIGH" : 0.3}
            ]
        },
        "LOW" :
        {
            "part" : 0.3,
            "subparts":
            [
                {"kinda LOW" : 0.4},
                {"really LOW" : 0.6}
            ]
        }
    }
    Out of this kind of json input, it shows each layer of the graph in a different color
    """

    current_label_changed = Signal(str)

    EXAMPLE_DATA = [
        {
            "label": "HIGH",
            "part" : 0.7,
            "color" : 0,
            "subparts":
            [
                {
                    "parent" : "HIGH",
                    "label" : "not so HIGH",
                    "part" : 0.4,
                    "color" : 0,
                    # "subparts":
                    # [
                    #     {
                    #         "parent" : "not so HIGH",
                    #         "label" : "whatever",
                    #         "part" : 0.5,
                    #         "color" : 0
                    #     },
                    #     {
                    #         "parent" : "not so HIGH",
                    #         "label" : "other",
                    #         "part" : 0.5,
                    #         "color" : 0
                    #     }
                    # ]
                },
                {
                    "parent" : "HIGH",
                    "label" : "mildly HIGH",
                    "part" : 0.2,
                    "color" : 0
                },
                {
                    "parent" : "HIGH",
                    "label" : "somehow HIGH",
                    "part" : 0.1,
                    "color" : 0
                },
                {
                    "parent" : "HIGH",
                    "label" : "pretty HIGH",
                    "part" : 0.3,
                    "color" : 0
                }
            ]
        },
        {
            "label" : "LOW",
            "part" : 0.3,
            "color" : 180,
            "subparts":
            [
                {
                    "parent" : "LOW",
                    "label" : "kinda LOW",
                    "part" : 0.4,
                    "color" : 180,
                    "subparts" :
                    [
                        {
                            "parent" : "kinda LOW",
                            "label" : "just a test",
                            "part" : 0.2
                        },
                        {
                            "parent" : "kinda LOW",
                            "label" : "another test",
                            "part" : 0.5,
                        },
                        {
                            "parent" : "kinda LOW",
                            "label" : "Owww yeeeeaahhh",
                            "part" : 0.1
                        }
                    ]
                },
                {
                    "parent" : "LOW",
                    "label" : "really LOW",
                    "part" : 0.6,
                    "color" : 180
                }
            ]
        }
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._data = {}
        self._visible_tree = {} # Holds the sub-tree we want to show to the user
        self.mouse_pos = None
        self._selected_path = None

        self._selected_label = ""
        self._area = QRect(0,0,0,0)

        self.setMouseTracking(True)
        # self.painter_paths = []
        self._painter_paths = {}
        #self._max_depth = 10 # Above 10 rings, the data is not readable...

        self.build_chart()

    def set_data(self, data: dict):
        self._data = data
        self._visible_tree = data
        self.build_chart()
        # self.arc_paths = []
        self.update()

    def create_layer(self,rect: QRect,layer:list,depth:int,inner_most_radius:int,width:int):
        """
        Adds a ring of width :width: after skipping depth rings from inner_most_radius
        :depth: ring index of this layer. 0 means it is the inner_most ring, displaying the data from the very first element of tree
        :tree: a dict of dicts, containing recursively all the nodes of the data to display. For each node, required keys are label and part. Optionnals include color and subparts
        :inner_most_radius: the interior radius of the very first ring
        """
        inner_radius = inner_most_radius + depth * width
        outer_radius = inner_radius + width
        start_angle = 0
        parent_name = None
        parent_part = 1.0 # Remember, each part is relative to the previous depth's part (absolute if depth is 0)
        
        self._painter_paths[depth] = {}

        if depth > 0:
            parent_name = layer[0]["parent"]
            parent_part = self._painter_paths[depth-1][parent_name]["relative_part"] # The angle of the ring is proportionnal to the one of its parent, and so on !
            start_angle = self._painter_paths[depth-1][parent_name]["start_angle"] # We want the child ring to start at the same angle as its parent

        for cell in layer:
            label = cell["label"]
            part = cell["part"]

            color_saturation = 100
            if label == self._selected_label:
                color_saturation = 255
            
            hue = start_angle

            if "color" in cell:
                hue = int(cell["color"])%360

            relative_part = parent_part * part
            span_angle = relative_part * 360
            
            self._painter_paths[depth][label] = {
                                            "part" : part,
                                            "relative_part" : relative_part,
                                            "start_angle" : start_angle,
                                            "color" : {"h":hue,"s":100,"v":int(255/(depth+1))},
                                            "span_angle" : span_angle,
                                            "path" : SunburstWidget.create_arc_path(rect,inner_radius,outer_radius,start_angle,span_angle)
                                        }

            # if label=="somehow HIGH":
            #     print(start_angle,span_angle)

            #print(f"Just drew {label} with angle from {start_angle} to {start_angle+span_angle}")
            if "subparts" in cell:
                self.create_layer(rect,cell["subparts"],depth+1,inner_most_radius,width)
                #cell["subparts"]["parent"]=cell["label"]
                
            
            start_angle += span_angle

    def resizeEvent(self,event:QResizeEvent):
        """
        Called every time the widget gets resized, even at the construction.
        Responsible for adjusting the drawing shape of the widget, and updating the plot accordingly.
        """
        side = min(event.size().toTuple())
        self._area = QRect(0,0,side,side)
        self._area.moveCenter(self.rect().center())
        self.build_chart()

    def build_chart(self):
        """
        Should be called everytime 
        """
        side = min(self.rect().size().toTuple())

        self.create_layer(self._area,self._visible_tree,0,side/8,side/8)


        # r1 = side / 2
        # r2 = r1 + side / 4

        # start_angle = 0

        # for angle in [0.5, 0.4, 0.1]:

        #     painter_path = SunburstWidget.create_arc_path(
        #         area, r1, r2, start_angle, angle * 360
        #     )

        #     self.painter_paths.append(painter_path)

        #     start_angle += angle * 360

    def paintEvent(self, event: QPaintEvent):

        painter = QPainter()
        painter.begin(self)

        painter.setRenderHint(QPainter.Antialiasing)
        brush = QBrush()

        for depth in self._painter_paths:# Draw every layer
            for label in self._painter_paths[depth]: # For each layer, loop through all of its labels
                path = self._painter_paths[depth][label]["path"]
                h,s,v = self._painter_paths[depth][label]["color"].values()
                color = QColor.fromHsv(h,s,v)
                painter.fillPath(path,color)


        # for i, path in enumerate(self.painter_paths):
        #     painter.fillPath(path, QColor(i * 100, 255, 255))

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
        side = min(self.rect().size().toTuple())

        x,y = event.pos().toTuple()
        xc,yc = self.rect().center().toTuple()

        radius = sqrt((x-xc)**2+(y-yc)**2) # get the distance between the mouse and the center of the widget

        previously_selected_label = self._selected_label

        self._selected_label = "" # If the mouse moves, it means (potentially) that the previously selected label may not be anymore

        #if radius >= side/8: # The mouse is not inside the center disc, so we need to know which ring/label was selected 
        for depth in self._painter_paths:# Check at every layer
            for label in self._painter_paths[depth]: # For each layer, loop through its labels
                if self._painter_paths[depth][label]["path"].contains(event.pos()): # Find the painter path drawn at this depth, for this label
                    self._selected_label = label # There we have it. The selected label !
                    self._painter_paths[depth][label]["color"]["s"]=255
                else:
                    self._painter_paths[depth][label]["color"]["s"]=100
        
        self.update() # Update the graph, only if the mouse was not in the center. We update it even if the mouse doesn't touch any label (in that case, it will be desaturated)

        if self._selected_label != previously_selected_label:
            self.current_label_changed.emit(self._selected_label)
        # x, y = event.localPos().x(), event.localPos().y()
        # xc = self.geometry().width() / 2
        # yc = self.geometry().height() / 2

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
    window = QWidget()
    layout = QVBoxLayout(window)

    label = QLabel("Selected label :")
    label.setSizePolicy(QSizePolicy(QSizePolicy.Expanding,QSizePolicy.Fixed))

    sunburst = SunburstWidget(window)
    sunburst.set_data(SunburstWidget.EXAMPLE_DATA)
    sunburst.current_label_changed.connect(lambda label_name:label.setText(f"Selected label : {label_name}"))
    sunburst.setSizePolicy(QSizePolicy(QSizePolicy.Expanding,QSizePolicy.Expanding))
    sunburst.show()

    layout.addWidget(label)
    layout.addWidget(sunburst)

    window.setLayout(layout)
    
    window.show()
    return app.exec_()


if __name__ == "__main__":
    exit(main(sys.argv))
