from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *

import sys


class RangeSlider(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.first_option = QStyleOptionSlider()
        self.second_option = QStyleOptionSlider()

        self.second_option.sliderPosition = 50
        self.first_option.sliderPosition = 10

    def paintEvent(self, event: QPaintEvent):

        painter = QPainter(self)

        # Draw rule
        opt = QStyleOptionSlider()
        opt.initFrom(self)
        opt.minimum = 0
        opt.maximum = 100
        opt.rect = self.rect()
        opt.subControls = QStyle.SC_SliderGroove
        self.style().drawComplexControl(QStyle.CC_Slider, opt, painter)

        # Draw first handle
        self.first_option.rect = self.rect()
        self.first_option.maximum = 100
        self.first_option.subControls = QStyle.SC_SliderHandle
        self.style().drawComplexControl(QStyle.CC_Slider, self.first_option, painter)

        # Draw second handle
        self.second_option.rect = self.rect()
        self.second_option.subControls = QStyle.SC_SliderHandle
        self.second_option.maximum = 100
        self.second_option.minimum = 0
        # self.second_option.sliderPosition = 50
        self.style().drawComplexControl(QStyle.CC_Slider, self.second_option, painter)

    def mousePressEvent(self, event: QMouseEvent):

        self._first_sc = self.style().hitTestComplexControl(
            QStyle.CC_Slider, self.first_option, event.pos(), self
        )
        self._second_sc = self.style().hitTestComplexControl(
            QStyle.CC_Slider, self.second_option, event.pos(), self
        )

    def mouseMoveEvent(self, event: QMouseEvent):

        pos = self.style().sliderValueFromPosition(
            0, 100, event.pos().x(), self.rect().width()
        )

        if self._first_sc == QStyle.SC_SliderHandle:
            self.first_option.sliderPosition = pos
            self.update()
            return

        if self._second_sc == QStyle.SC_SliderHandle:
            self.second_option.sliderPosition = pos
            self.update()
            return


if __name__ == "__main__":

    app = QApplication(sys.argv)

    w = RangeSlider()
    w.show()

    app.exec_()
