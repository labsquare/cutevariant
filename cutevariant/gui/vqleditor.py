from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *


from .abstractquerywidget import AbstractQueryWidget
from cutevariant.core import Query
from cutevariant.core import sql

import re


class VqlSyntaxHighlighter(QSyntaxHighlighter):
    def __init__(self, document=None):
        super().__init__(document)

    def highlightBlock(self, text):
        """override """

        palette = qApp.palette("QTextEdit")

        REGEXES = {
            "SELECT|FROM|WHERE": (QFont.Bold, palette.color(QPalette.HighlightedText))
        }
        for regex, (style, color) in REGEXES.items():
            rule = QRegularExpression(regex)
            matchIterator = rule.globalMatch(text)
            while matchIterator.hasNext():
                match = matchIterator.next()
                t_format = QTextCharFormat()
                t_format.setFontWeight(style or QFont.Normal)
                t_format.setForeground(color or Qt.black)
                self.setFormat(match.capturedStart(), match.capturedLength(), t_format)


class VqlEditor(AbstractQueryWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Columns")
        self.text_edit = QTextEdit()
        self.highlighter = VqlSyntaxHighlighter(self.text_edit.document())

        main_layout = QVBoxLayout()

        main_layout.addWidget(self.text_edit)
        self.setLayout(main_layout)

        self.text_edit.textChanged.connect(self.changed)

    def setQuery(self, query: Query):
        """ Method override from AbstractQueryWidget"""
        self.query = query
        self.text_edit.setPlainText(self.query.to_vql())

    def getQuery(self):
        """ Method override from AbstractQueryWidget"""
        query = self.query.from_vql(self.text_edit.toPlainText())

        return self.query
