from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

from cutevariant import constants as cst


class SplashScreen(QSplashScreen):
    def __init__(self, parent=None):
        super().__init__()
        self.setPixmap(QPixmap(cst.DIR_ICONS + "splash.png"))

    def paintEvent(self, event: QPaintEvent):
        super().paintEvent(event)

        painter = QPainter(self)

        message = "Chargement ... "
        rect = painter.fontMetrics().boundingRect(message)
        rect.moveCenter(QPoint(self.rect().center().x(), self.rect().center().y() + 60))
        painter.setPen(QPen(QColor("white")))
        painter.drawText(rect, Qt.AlignCenter, message)

        message = f"Version Rosalind {QApplication.applicationVersion()}"
        rect = painter.fontMetrics().boundingRect(message)
        rect.moveBottomRight(self.rect().bottomRight() - QPoint(5, 5))
        painter.drawText(rect, Qt.AlignCenter, message)
