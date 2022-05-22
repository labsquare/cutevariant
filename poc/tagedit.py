from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from functools import partial


class FlowLayout(QLayout):
    def __init__(self, parent=None, margin=0, spacing=-1):
        super().__init__(parent)

        if parent is not None:
            self.setMargin(margin)

        self.setSpacing(spacing)

        self.itemList = []

    def __del__(self):
        item = self.takeAt(0)
        while item:
            item = self.takeAt(0)

    def addItem(self, item):
        self.itemList.append(item)

    def count(self):
        return len(self.itemList)

    def itemAt(self, index):
        if index >= 0 and index < len(self.itemList):
            return self.itemList[index]

        return None

    def takeAt(self, index):
        if index >= 0 and index < len(self.itemList):
            return self.itemList.pop(index)

        return None

    def expandingDirections(self):
        return Qt.Orientations(Qt.Orientation(0))

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        height = self._doLayout(QRect(0, 0, width, 0), True)
        return height

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._doLayout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()

        for item in self.itemList:
            size = size.expandedTo(item.minimumSize())

        self.margin = 5
        size += QSize(2 * self.margin, 2 * self.margin)
        return size

    def _doLayout(self, rect, testOnly):
        x = rect.x()
        y = rect.y()
        lineHeight = 0

        for item in self.itemList:
            wid = item.widget()
            spaceX = self.spacing() + wid.style().layoutSpacing(
                QSizePolicy.PushButton, QSizePolicy.PushButton, Qt.Horizontal
            )

            spaceY = self.spacing() + wid.style().layoutSpacing(
                QSizePolicy.PushButton, QSizePolicy.PushButton, Qt.Vertical
            )

            nextX = x + item.sizeHint().width() + spaceX
            if nextX - spaceX > rect.right() and lineHeight > 0:
                x = rect.x()
                y = y + lineHeight + spaceY
                nextX = x + item.sizeHint().width() + spaceX
                lineHeight = 0

            if not testOnly:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))

            x = nextX
            lineHeight = max(lineHeight, item.sizeHint().height())

        return y + lineHeight - rect.y()


class TagItem(QLabel):
    def __init__(self, word: str, parent=None):
        super().__init__(parent)

        self.word = word
        self.font = QFont()
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.setMouseTracking(True)
        self.hover = False

        self.setTextInteractionFlags(Qt.TextEditable)

    def paintEvent(self, event: QPaintEvent):
        """override"""

        painter = QPainter(self)
        painter.setFont(self.font)
        round_rect = self.rect().adjusted(4, 4, -4, -4)

        painter.setBrush(QColor("#E0EAF1"))
        painter.setPen(Qt.NoPen)
        painter.drawRect(round_rect)
        painter.setPen(QColor("#80A3BB"))

        # draw icon
        cross_icon = self.style().standardIcon(QStyle.SP_TitleBarCloseButton)
        painter.drawPixmap(
            self.rect().right() - 20,
            self.rect().center().y() - 7,
            cross_icon.pixmap(16, 16),
        )

        painter.drawText(round_rect.adjusted(-10, 0, 0, 0), Qt.AlignCenter, self.word)
        super().paintEvent(event)

    def sizeHint(self):
        """override"""
        return self.word_size() + QSize(40, 15)

    def word_size(self):
        metric = QFontMetrics(self.font)
        return QSize(metric.width(self.word), metric.height())

    def mouseMoveEvent(self, event: QMouseEvent):
        """override"""
        pass

    def mousePressEvent(self, event: QMouseEvent):
        """override"""
        pass

    def enterEvent(self, event: QMouseEvent):
        """override"""
        pass

    def leaveEvent(self, event: QEvent):
        """override"""
        pass


class TagEdit(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.flow_layout = FlowLayout()

        pal = self.palette()
        pal.setBrush(QPalette.WindowText, Qt.white)
        self.setPalette(pal)

        self.items = []
        self.setLayout(self.flow_layout)

    def add_item(self, item: TagItem):
        self.items.append(item)
        self.flow_layout.addWidget(item)

    def add_tag(self, tag: str):
        self.add_item(TagItem(tag))


if __name__ == "__main__":

    import sys

    app = QApplication(sys.argv)
    w = TagEdit()
    w.add_tag("sacha")
    w.add_tag("boby")
    w.add_tag("olivier")
    w.add_tag("Valentin")

    w.show()

    sys.exit(app.exec_())
