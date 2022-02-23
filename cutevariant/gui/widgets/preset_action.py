from PySide6.QtWidgets import QLabel, QWidget, QToolButton, QWidgetAction, QHBoxLayout
from PySide6.QtCore import Signal, QObject
from PySide6.QtGui import *

import typing


class PresetMenuWidget(QWidget):

    removed = Signal()
    triggered = Signal()

    def __init__(self, text: str, data: typing.Any, parent=None):
        super().__init__(parent)
        self.data = data
        self.label = QLabel(text)
        self.button = QToolButton()
        self.button.setFocusPolicy(Qt.NoFocus)
        self.button.setAutoRaise(True)
        self.button.clicked.connect(self.removed)

        layout = QHBoxLayout(self)
        layout.addWidget(self.label)
        layout.setContentsMargins(10, 0, 0, 0)
        layout.addWidget(self.button)

        self.setMouseTracking(True)

    def __set_hover(self, enabled=True):
        self.setBackgroundRole(QPalette.Highlight if enabled else QPalette.Window)
        self.setAutoFillBackground(enabled)

    def enterEvent(self, event):
        self.__set_hover(True)

    def leaveEvent(self, event):
        self.__set_hover(False)

    def showEvent(self, event):
        self.__set_hover(False)

    def mousePressEvent(self, event):

        if self.label.rect().contains(event.pos()):
            self.triggered.emit()

        return super().mousePressEvent(event)


class PresetAction(QWidgetAction):

    triggered = Signal()
    removed = Signal()

    def __init__(self, text: str, data: typing.Any, parent: QObject):
        super().__init__(parent)

        self.w = PresetMenuWidget(text, data, parent)
        self.w.triggered.connect(self.triggered)
        self.w.removed.connect(self.removed)
        self.w.data = data
        self.setDefaultWidget(self.w)

    def data(self):
        return self.w.data

    def text(self):
        return self.w.label.text()

    def set_close_icon(self, icon: QIcon):
        self.w.button.setIcon(icon)
