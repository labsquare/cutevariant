from PySide6.QtWidgets import QTextEdit
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QBrush, QFont, QSyntaxHighlighter, QFontMetrics, QTextCharFormat
import sys

import re


class TagEditSyntaxHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)

    def highlightBlock(self, text: str) -> None:

        f = QTextCharFormat()
        f.setBackground(QBrush(QColor("#D5E9F5")))
        f.setForeground(QBrush(QColor("D5E9F5").darker().darker()))
        f.setFontWeight(QFont.Bold)
        for match in re.finditer(r"([^,]+)", text):
            start, end = match.span()
            self.setFormat(start, (end - start), f)


class TagEdit(QTextEdit):
    def __init__(self, parent=None):
        super().__init__()

        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setLineWrapMode(QTextEdit.NoWrap)
        self.setPlaceholderText("Tags separated by comma ... ")

        self.syntax = TagEditSyntaxHighlighter(self.document())

        metric = QFontMetrics(self.font())

        self.setFixedHeight(metric.height() + 10)

    def text(self):
        return self.toPlainText()
