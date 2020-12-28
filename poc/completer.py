from PySide2.QtWidgets import *
from PySide2.QtGui import *
from PySide2.QtCore import *
import sys


class Completer(QWidget):
    """docstring for ClassName"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlag(Qt.Popup)
        self.setFocusPolicy(Qt.NoFocus)
        self.w = None
        self.view = QListView()
        self.view.setFocusPolicy(Qt.NoFocus)
        self.view.installEventFilter(self)
        self.setFocusProxy(self.view)
        self.model = QStringListModel(["salut", "boby"])
        self.view.setModel(self.model)
        vlayout = QHBoxLayout()
        vlayout.setContentsMargins(0, 0, 0, 0)
        vlayout.addWidget(self.view)
        vlayout.addWidget(QLabel("salut"))
        self.setLayout(vlayout)

        self.resize(100, 200)

    def eventFilter(self, o, e):

        if "TextEdit" in str(o):
            if e.type() == QEvent.FocusOut:
                return True
            else:
                o.event(e)
                return True

        if "QListView" in str(o):
            if e.type() == QEvent.KeyPress:
                self.w.event(e)


class TextEdit(QTextEdit):
    """docstring for ClassName"""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.mycompleter = Completer()
        self.mycompleter.w = self
        self.installEventFilter(self.mycompleter)

        self.resize(800, 400)

    def keyPressEvent(self, event):

        self.mycompleter.move(self.mapToGlobal(self.cursorRect().center()))

        if not self.mycompleter.isVisible():
            self.mycompleter.show()
            self.mycompleter.setFocus()

        super().keyPressEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)

    w = TextEdit()
    w.show()

    app.exec_()
