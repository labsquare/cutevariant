from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

import math
import networkx as nx
import igraph as ig


class Node(QGraphicsItem):
    def __init__(self, name, parent=None):
        super().__init__(parent)
        self._name = name
        self.edges = []

        self.color = "red" if name.startswith("union") else "#2FB4AE"
        self.radius = 30 if name.startswith("union") else 30
        self._rect = QRect(0, 0, self.radius * 2, self.radius * 2)

        self.setFlag(self.ItemIsMovable)
        self.setFlag(self.ItemSendsGeometryChanges)
        self.setCacheMode(self.DeviceCoordinateCache)

    def boundingRect(self):
        return self._rect

    def paint(self, painter, option, widget=None):
        painter.setRenderHints(QPainter.Antialiasing)
        painter.setPen(
            QPen(
                QColor("#2FB4AE").darker(),
                2,
                Qt.SolidLine,
                Qt.RoundCap,
                Qt.RoundJoin,
            )
        )
        painter.setBrush(QBrush(QColor(self.color)))
        painter.drawEllipse(self.boundingRect())
        painter.setPen(QPen(QColor("white")))
        painter.drawText(self.boundingRect(), Qt.AlignCenter, self._name)

    def add_edge(self, edge):
        self.edges.append(edge)

    def itemChange(self, change, value):

        if change == self.ItemPositionHasChanged:
            for edge in self.edges:
                edge.adjust()

        return super().itemChange(change, value)


class Edge(QGraphicsItem):
    def __init__(self, source, dest, parent=None):
        super().__init__(parent)
        self.source = source
        self.dest = dest

        self.height = 2
        self.color = "#b7b7b8"
        self.arrowSize = 20

        self.source.add_edge(self)
        self.dest.add_edge(self)

        self.line = QLineF()

        self.setZValue(-1)

        self.adjust()

    def boundingRect(self):

        return (
            QRectF(self.line.p1(), self.line.p2())
            .normalized()
            .adjusted(
                -self.height - self.arrowSize,
                -self.height - self.arrowSize,
                self.height + self.arrowSize,
                self.height + self.arrowSize,
            )
        )

    def adjust(self):
        self.prepareGeometryChange()
        self.line = QLineF(
            self.source.pos() + self.source.boundingRect().center(),
            self.dest.pos() + self.dest.boundingRect().center(),
        )
        # self.update()

    def draw_arraow(self, painter, start, end):

        painter.setBrush(QBrush(self.color))

        line = QLineF(end, start)

        angle = math.atan2(-line.dy(), line.dx())
        arrowP1 = line.p1() + QPointF(
            math.sin(angle + math.pi / 3) * self.arrowSize,
            math.cos(angle + math.pi / 3) * self.arrowSize,
        )
        arrowP2 = line.p1() + QPointF(
            math.sin(angle + math.pi - math.pi / 3) * self.arrowSize,
            math.cos(angle + math.pi - math.pi / 3) * self.arrowSize,
        )

        center = (arrowP1 - arrowP2) / 2

        arrowHead = QPolygonF()
        arrowHead.clear()
        arrowHead.append(line.p1())
        arrowHead.append(arrowP1)
        arrowHead.append(arrowP2)
        painter.drawLine(line)
        painter.drawPolygon(arrowHead)

        painter.setPen(
            QPen(
                QColor("red"),
                10,
                Qt.SolidLine,
                Qt.RoundCap,
                Qt.RoundJoin,
            )
        )

    def paint(self, painter, option, widget=None):

        if self.source and self.dest:
            painter.setRenderHints(QPainter.Antialiasing)

            painter.setPen(
                QPen(
                    QColor(self.color),
                    self.height,
                    Qt.SolidLine,
                    Qt.RoundCap,
                    Qt.RoundJoin,
                )
            )
            painter.drawLine(self.line)

            self.draw_arraow(painter, self.line.p1(), self.get_target())

    def get_target(self):
        target = self.line.p1()
        center = self.line.p2()
        radius = self.dest.radius
        vector = target - center
        length = math.sqrt(vector.x() ** 2 + vector.y() ** 2)
        normal = vector / length
        target = QPointF(
            center.x() + (normal.x() * radius), center.y() + (normal.y() * radius)
        )
        return target


class PedView(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__()

        scene = QGraphicsScene()

        self.setScene(scene)

        self.load()

        self.resize(600, 600)

    def load(self):

        graph = nx.DiGraph()
        graph.add_edges_from(
            [
                ("Grand Pere", "union1"),
                ("Grand Mere", "union1"),
                ("union1", "union1b"),
                ("union1b", "Tonton"),
                ("union1b", "Papa"),
                ("Papa", "union2"),
                ("Maman", "union2"),
                ("union2", "Fiston"),
            ]
        )

        # pos = nx.spring_layout(graph, iterations=5000, scale=100, k=50)
        h = ig.Graph.from_networkx(graph)

        layout = h.layout_sugiyama()
        layout.scale(60)
        pos = layout.coords

        nodes = {}
        for i in h.vs():
            node = i["_nx_name"]
            item = Node(node)
            x, y = pos[i.index]
            item.setPos(float(x), float(y))
            self.scene().addItem(item)
            nodes[i.index] = item

        for a, b in h.get_edgelist():
            source = nodes[a]
            dest = nodes[b]

            self.scene().addItem(Edge(source, dest))

        # nodes = {}
        # for node in graph:
        #     item = Node(node)
        #     x, y = pos[node]
        #     item.setPos(float(x), float(y))
        #     self.scene().addItem(item)
        #     nodes[node] = item

        # for a, b in graph.edges:

        #     source = nodes[a]
        #     dest = nodes[b]

        #     self.scene().addItem(Edge(source, dest))


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)

    view = PedView()
    view.show()

    app.exec()
