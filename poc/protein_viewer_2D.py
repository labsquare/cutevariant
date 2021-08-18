import sys
import requests
import json
import urllib.parse
import urllib.request
from PySide2.QtWidgets import *
from PySide2.QtGui import *
from PySide2.QtCore import *


class PfamWidget(QWidget):
    """Widget display PFAM"""

    def __init__(self, prot_name: str, parent=None) -> None:
        """init variables and parameter

        Args:
            prot_name (str): protein name to load
        """
        super().__init__()

        # Constant
        self.y_position = 100  # Value betwenn 25 and 90
        self.y_height = 70  # height of the PFAM
        self.scaling = 2  # protein to pixel

        # Load
        self.load(prot_name)

        # Data index
        """self.variants = [
            {"name": "G32X", "position": 150, "height": 60, "color": "red"},
            {"name": "G31X", "position": 50, "height": 60, "color": "green"},
            {"name": "G30X", "position": 250, "height": 60, "color": "blue"},
        ] """

        self.variants = []

        # Data group
        """self.groups = [
            {
                "name": "Mutation",
                "color": "red",
            }
        ]"""
        self.groups = []

        # Parameter
        self.resize(600, 250)
        self.setMouseTracking(True)

    def paintEvent(self, event: QPaintEvent):
        """Override"""
        # QPainter
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Legend
        x_legend = self.rect().left()
        y_legend = self.rect().bottom()
        for group in self.groups:
            painter.setPen(QPen(QColor(group["color"])))
            painter.setBrush(QBrush(QColor(group["color"])))
            painter.drawEllipse(x_legend, y_legend - 10, 10, 10)
            painter.setPen(QPen(Qt.black))
            painter.drawText(x_legend + 15, y_legend, group["name"])
            x_legend += 85

        # Painting region
        start = 0
        end = self.data[0]["length"]
        for domain in self.domains:
            painter.setPen(QPen(Qt.black))
            painter.setBrush(QBrush(Qt.gray))
            painter.drawRect(
                QRect(
                    QPoint(self.protein_to_pixel(start), self.y_position),
                    QSize(
                        self.protein_to_pixel(domain["start"] - start), self.y_height
                    ),
                )
            )
            painter.setBrush(QBrush(QColor(domain["color"])))
            region = self.domain_to_QRect(domain)
            painter.drawRect(region)
            painter.setPen(QPen(Qt.black))
            font = QFont()
            font.setPixelSize(10)
            painter.setFont(font)
            painter.drawText(region, Qt.AlignCenter, domain["name"])
            start = domain["end"]
        painter.setBrush(QBrush(Qt.gray))
        painter.drawRect(
            QRect(
                QPoint(self.protein_to_pixel(start), self.y_position),
                QSize(
                    self.protein_to_pixel(end - start),
                    self.y_height,
                ),
            )
        )

        # Scale painted
        self.y_scale_position = self.rect().bottom() - 50
        y_scale_height = 15
        index = 0
        painter.setPen(QPen(Qt.gray))
        line = QLine(
            self.protein_to_pixel(0),
            self.y_scale_position,
            self.protein_to_pixel(end),
            self.y_scale_position,
        )
        painter.drawLine(line)
        while index < end - 20:
            index += 20
            painter.drawLine(
                QLine(
                    self.protein_to_pixel(index),
                    self.y_scale_position,
                    self.protein_to_pixel(index),
                    self.y_scale_position - y_scale_height + 10,
                )
            )
            if index % 100 == 0:
                painter.drawLine(
                    QLine(
                        self.protein_to_pixel(index),
                        self.y_scale_position,
                        self.protein_to_pixel(index),
                        self.y_scale_position - y_scale_height,
                    )
                )
                painter.drawText(
                    self.protein_to_pixel(index - 5),
                    self.y_scale_position + 10,
                    30,
                    10,
                    Qt.AlignLeft,
                    str(index),
                )
            painter.drawText(
                self.protein_to_pixel(end - 5),
                self.y_scale_position + 10,
                30,
                10,
                Qt.AlignLeft,
                str(end),
            )

        # Add index
        for variant in self.variants:

            self.paint_index(
                variant["position"],
                variant["height"],
                variant["color"],
            )

    # Fonctions
    def add_group(self, name: str, color: str) -> None:
        """add a new group legend

        Args:
            name (str): group name
            color (str): group color
        """
        self.groups.append(
            {
                "name": name,
                "color": color,
            }
        )
        self.update()

    def add_index(
        self, name: str, position: int, color_given: str, height: int = 60
    ) -> None:
        """add a new index to the dictionnary

        Args:
            name (str): index name
            position (int): index position
            color_given (str): color to print the index
            height (int, optional): index height. Defaults to 60.
        """
        self.variants.append(
            {"name": name, "position": position, "height": height, "color": color_given}
        )

    def paint_index(self, position: int, height: int, color: str) -> None:
        """paint an index in the PFAM

        Args:
            position (int): index position
            height (int): index height
            color (str): index color to print
        """
        position = self.protein_to_pixel(position)
        painter = QPainter(self)
        painter.setPen(QPen(QColor(color)))
        painter.setBrush(QBrush(QColor(color)))
        painter.drawLine(
            QLine(position, self.y_position, position, self.y_position - height)
        )
        painter.drawEllipse(position - 2, self.y_position - height, 5, 5)

    def distance(self, x1: float, y1: float, x2: float, y2: float) -> float:
        """square distances between 2 points (x1,y1) and (x2,y2)

        Args:
            x1 (float): x-axis of the first pointin pixel
            y1 (float): y-axis of the first point in pixel
            x2 (float): x-axis of the second point in pixel
            y2 (float): y-axis of the second point in pixel

        Returns:
            [float]: distances
        """
        # square distances between 2 points (x1,y1), (x2,y2)
        return (x1 - x2) ** 2 + (y1 - y2) ** 2

    def protein_to_pixel(self, value: float) -> float:
        """transform protein coord into pixel coord

        Args:
            value (float): scaling value

        Returns:
            [float]: pixel coord
        """
        return value * self.scaling

    def pixel_to_protein(self, value: float) -> float:
        """transform pixel coord into protein coord

        Args:
            value (float): scaling value

        Returns:
            float: protein coord
        """
        if self.scaling != 0:
            return value * 1 / self.scaling

    def domain_to_QRect(self, domain: dict) -> QRect:
        """create QRect from a dictionary with start and end point

        Args:
            domain (dict): domain with starting point and ending point

        Returns:
            QRect: Rect to draw
        """
        return QRect(
            QPoint(self.protein_to_pixel(domain["start"]), self.y_position),
            QSize(
                self.protein_to_pixel(domain["end"] - domain["start"]),
                self.y_height,
            ),
        )

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """event to show more information on click about index and domain

        Args:
            event (QMouseEvent): Press event
        """
        # Print more information about index
        for variant in self.variants:
            if (
                self.distance(
                    event.x(),
                    event.y(),
                    self.protein_to_pixel(variant["position"]),
                    self.y_position - variant["height"],
                )
                < 10
                and event.button() == Qt.LeftButton
            ):
                QToolTip.showText(
                    event.globalPos(),
                    variant["name"] + "   position : " + str(variant["position"]),
                )

        # Print more information about domain
        for domain in self.domains:
            if self.domain_to_QRect(domain).contains(event.x(), event.y(), False):
                QToolTip.showText(event.globalPos(), domain["name"])

    def get_pfam(self, name_prot: str) -> json:
        """get the json from the prot_name in the pfam database

        Args:
            name_prot (str): protein name

        Returns:
            json: json to extract
        """
        r = requests.get(f"https://pfam.xfam.org/protein/" + name_prot + "/graphic")
        if r.status_code == 200:
            return r.json()
        else:
            print("Echec request")
            return None

    def load(self, prot_name) -> None:
        """load PFAM from protein or ID"""
        # self.data = self.get_pfam(prot_name)
        self.data = json.load(open("graphic.json"))
        self.domains = []
        for data in self.data[0]["regions"]:
            self.domains.append(
                {
                    "name": data["text"],
                    "start": data["start"],
                    "end": data["end"],
                    "color": data["colour"],
                }
            )
        print(self.domains)
        print("end_loading")

    def gene_to_protein(
        self, fromf: str, to: str, query: str, format: str = "tab"
    ) -> None:
        """transcript data form one database to others

        Args:
            fromf (str): initial database
            to (str): target database
            query (str): name to transcript
            format (str, optional): [description]. Defaults to "tab".
        """
        # Permet l'extraction des noms des protéines
        # DOC :https://www.uniprot.org/help/api_idmapping
        url = "https://www.uniprot.org/uploadlists/"

        params = {"from": fromf, "to": to, "format": format, "query": query}

        data = urllib.parse.urlencode(params)
        data = data.encode("utf-8")
        req = urllib.request.Request(url, data)
        with urllib.request.urlopen(req) as f:
            response = f.read()
        print(response.decode("utf-8"))
        return None


if __name__ == "__main__":

    app = QApplication(sys.argv)
    widget = PfamWidget("EGFR_HUMAN")
    # Test Fonction
    """widget.add_group("New Group", "blue")
    widget.add_index("added", 350, "red", 40)"""
    widget.show()
    app.exec_()
