import requests
import io
import pandas as pd
import math

# url = "https://ldlink.nci.nih.gov/LDlinkRest/ldmatrix"


# rs = [
#     "rs12980275",
#     "rs8109886",
#     "rs4803222",
#     "rs111531283",
#     "rs8099917",
#     "rs7248668",
#     "rs35963157",
#     "rs955155",
#     "rs8101517",
#     "rs6508852",
# ]

# data = {"pop": "CEU", "r2_d": "d", "token": "9e88a9311435", "snps": "\n".join(rs)}


# r = requests.get(url, params=data)


from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *
import sys


class HaploWidget(QWidget):
    """docstring for ClassName"""

    def __init__(self, parent=None):
        super().__init__(parent)

        # content = b"""
        # RS_number\trs148890987\trs3\trs4
        # rs148890987\t1.0\t0.707\t0.707
        # rs3\t0.707\t1.0\t1.0
        # rs4\t0.707\t1.0\t1.0
        # """
        # f = io.StringIO(content.decode("utf-8"))
        # self.df = pd.read_csv(f, sep="\t", index_col=0)

        self.size = 30
        self.mouse = None
        self.load()

    def load(self):
        url = "https://ldlink.nci.nih.gov/LDlinkRest/ldmatrix"

        rs = [
            "rs12980275",
            "rs8109886",
            "rs4803222",
            "rs111531283",
            "rs8099917",
            "rs7248668",
            "rs35963157",
            "rs955155",
            "rs8101517",
            "rs6508852",
        ]

        data = {
            "pop": "CEU",
            "r2_d": "d",
            "token": "FILL THE TOKEN",
            "snps": "\n".join(rs),
        }
        r = requests.get(url, params=data)
        f = io.StringIO(r.content.decode("utf-8"))
        self.df = pd.read_csv(f, sep="\t", index_col=0)

        # self.df = pd.read_csv("fake.csv")

    def paintEvent(self, event):

        painter = QPainter(self)

        painter.setBrush(QBrush(QColor("white")))
        painter.drawRect(self.rect())
        painter.setRenderHint(QPainter.HighQualityAntialiasing)

        item_count = len(self.df)

        bounding_rect = QRect(0, 0, item_count * self.size, item_count * self.size)

        transform = QTransform()
        transform.translate(self.rect().center().x(), self.rect().center().y() + 100)
        transform.rotate(-135)

        # transform.reset()

        painter.save()
        painter.setTransform(transform)
        if self.mouse:
            mouse = transform.inverted()[0].map(self.mouse)

        #        painter.drawRect(bounding_rect)

        for j in range(0, item_count):
            for i in range(0, item_count - j):
                rect = QRect(0, 0, self.size, self.size)

                x = i * self.size
                y = j * self.size

                rect.moveLeft(x)
                rect.moveTop(y)

                color = "red"
                if self.mouse:
                    if rect.contains(mouse):
                        color = "blue"

                painter.setBrush(QBrush(QColor(color)))
                painter.setPen(QPen(QColor("lightgray")))
                painter.drawRect(rect)

        painter.restore()

        painter.setPen(QPen(QColor("black")))
        y = -self.size * math.sqrt(2)
        for name in self.df.columns:
            painter.save()
            painter.translate(self.rect().center().x(), 20)
            painter.rotate(90)
            painter.drawText(0, y, name)
            painter.restore()
            y += self.size * math.sqrt(2)

    def mousePressEvent(self, event):

        self.mouse = event.pos()

        self.update()


if __name__ == "__main__":

    app = QApplication(sys.argv)

    w = HaploWidget()
    w.show()
    app.exec_()
