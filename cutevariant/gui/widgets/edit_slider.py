from PySide2.QtWidgets import (
    QWidget,
    QSlider,
    QApplication,
    QHBoxLayout,
    QAbstractSpinBox,
    QSpinBox,
)
from PySide2.QtCore import Qt

import sys


class EditSlider(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        hlayout = QHBoxLayout()
        hlayout.setContentsMargins(0, 0, 0, 0)
        hlayout.setSpacing(2)

        self.edit = QSpinBox()
        self.edit.setMinimumWidth(40)
        self.edit.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.slider = QSlider(Qt.Horizontal)

        hlayout.addWidget(self.edit)
        hlayout.addWidget(self.slider)

        self.setLayout(hlayout)

        self.slider.valueChanged.connect(self.setValue)
        self.edit.valueChanged.connect(self.setValue)

    def setRange(self, min_val, max_val):
        self.edit.setRange(min_val, max_val)
        self.slider.setRange(min_val, max_val)

    def value(self) -> int:
        return self.edit.value()

    def setValue(self, value: int):

        if self.sender() != self.slider and self.sender() != self.edit:
            self.edit.setValue(value)
            self.slider.setValue(value)
            return

        if self.sender() == self.slider:
            self.edit.setValue(value)

        if self.sender() == self.edit:
            self.slider.setValue(value)


if __name__ == "__main__":

    app = QApplication(sys.argv)

    w = EditSlider()
    w.show()

    # q = QSlider()
    # q.show()

    app.exec_()
