from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *

import sys


class Pane(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.widget = None
        self.label = QLabel()

        self.bar = QFrame()
        self.bar_layout = QHBoxLayout()
        self.bar_layout.setContentsMargins(0, 0, 0, 0)

        self.bar.setLayout(self.bar_layout)
        self.bar.setFrameShape(QFrame.NoFrame)

        # self.toolbar.setIconSize(QSize(16,16))
        # self.toolbar.setStyleSheet("background-color:palette(shadow); color: palette(light)")

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.setFrameShape(QFrame.Panel)
        self.setFrameShadow(QFrame.Raised)
        self.setLineWidth(1)
        self.setMidLineWidth(3)

        # build expand buttons
        expand_button = QToolButton()
        expand_button.setAutoRaise(True)
        expand_button.setIcon(
            self.style().standardIcon(QStyle.SP_TitleBarUnshadeButton)
        )
        expand_button.setIconSize(QSize(14, 14))
        expand_button.clicked.connect(self.toggle_visible)

        # setup label
        # self.label.setText(self.windowTitle())
        font = QFont()
        font.setBold(True)
        self.label.setFont(font)
        self.bar_layout.addWidget(expand_button)

        self.bar_layout.addWidget(self.label)
        # self.spacer = QWidget()
        # self.spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        # self.toolbar.addWidget(self.spacer)

        self.main_layout = QVBoxLayout()
        self.main_layout.addWidget(self.bar)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self.setLayout(self.main_layout)

    def toggle_visible(self):
        if self.widget:
            self.widget.setVisible(not self.widget.isVisible())

    def setWidget(self, widget):
        self.widget = widget
        self.main_layout.addWidget(self.widget)

    def setTitle(self, title: str):
        self.label.setText(title)


class TestPane(Pane):
    def create_widget(self):

        w = QWidget()
        l = QFormLayout()

        l.addRow("input", QSpinBox())
        l.addRow("frequenies", QSlider(Qt.Horizontal))
        w.setLayout(l)

        return w


class PanelListWidget(QScrollArea):
    def __init__(self, parent=None):
        super().__init__()
        self.panels = []
        self.viewport = QWidget()
        self.vlayout = QVBoxLayout()
        self.vlayout.setSpacing(1)
        self.vlayout.setContentsMargins(0, 0, 0, 0)
        self.viewport.setLayout(self.vlayout)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.spacer = QWidget()
        self.spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.vlayout.addWidget(self.spacer)
        self.vlayout.setSizeConstraint(QLayout.SetMaximumSize)

        self.setWidgetResizable(True)

        self.main_widget = QWidget()
        self.main_widget.setLayout(self.vlayout)

        self.setWidget(self.main_widget)

    def add(self, panel):
        self.panels.append(panel)
        self.vlayout.insertWidget(0, panel)
        panel.parent = self

    def clear(self):
        raise NotImplementedError("To Do @see #31")

    def indexOf(self, panel):
        self.panels.index(panel)


if __name__ == "__main__":

    app = QApplication(sys.argv)

    all_w = QTabWidget()

    w = PanelListWidget()

    w.add(TestPane())
    w.add(TestPane())
    w.add(TestPane())

    w2 = PanelListWidget()

    w2.add(TestPane())
    w2.add(TestPane())
    w2.add(TestPane())

    all_w.addTab(w, "Population")
    all_w.addTab(w2, "Samples")

    all_w.show()

    app.exec_()
