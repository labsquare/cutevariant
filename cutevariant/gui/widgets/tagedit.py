from PySide6.QtWidgets import (
    QHBoxLayout,
    QInputDialog,
    QLineEdit,
    QTextEdit,
    QCompleter,
    QStyle,
    QToolButton,
    QWidget,
)
from cutevariant import gui

from PySide6.QtCore import Qt, qCompress
from PySide6.QtGui import (
    QColor,
    QBrush,
    QFont,
    QStandardItem,
    QStandardItemModel,
    QSyntaxHighlighter,
    QFontMetrics,
    QTextCharFormat,
)
import sys
import re

from cutevariant.gui.ficon import FIcon


class TagEdit(QWidget):
    def __init__(self, parent=None):
        super().__init__()

        self.w = gui.widgets.MultiComboBox()
        self.w.setContentsMargins(0, 0, 0, 0)
        self.add_btn = QToolButton()
        self.add_btn.setText("+")
        self.add_btn.setIcon(FIcon(0xF0722))
        self.add_btn.clicked.connect(self.on_add)

        hlayout = QHBoxLayout(self)
        hlayout.addWidget(self.w)
        hlayout.addWidget(self.add_btn)
        hlayout.setContentsMargins(0, 0, 0, 0)
        hlayout.setSpacing(0)

    def setPlaceholderText(self, text: str):
        self.w.lineEdit().setPlaceholderText(text)

    def text(self) -> str:
        return self.w.text()

    def setText(self, text: str):
        self.w.set_text(text)

    def addItem(self, text, data=None) -> QStandardItem:
        return self.w.addItem(text, data)

    def addItems(self, texts, datalist=None):
        self.w.addItems(texts, datalist)

    def on_add(self):
        text, _ = QInputDialog.getText(self, "Create a new tag", "Tags:")
        if text and text not in self.w.words():
            item = self.w.addItem(text)
            # item.setForeground(QColor("red"))
            item.setCheckState(Qt.Checked)


if __name__ == "__main__":

    import sys
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)

    w = TagEdit()
    w.show()
    app.exec()
