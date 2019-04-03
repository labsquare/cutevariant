from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *


from .abstractquerywidget import AbstractQueryWidget
from cutevariant.core import Query
from cutevariant.core import sql


class VqlSyntaxHighlighter(QSyntaxHighlighter):
    """SQL Syntax highlighter rules"""

    def __init__(self, document=None):
        super().__init__(document)

        palette = qApp.palette("QTextEdit")

        # SQL Syntax highlighter rules
        # dict: pattern, font, color, minimal (not greedy)
        self.highlighting_patterns = [
            {
                # Keywords
                # \b allows to perform a "whole words only"
                'pattern': "|".join((f'\\b%s\\b' % keyword for keyword in [
                    'SELECT', 'FROM', 'WHERE', 'AS',
                    'AND', 'OR', 'NOT', 'ALL', 'ANY', 'BETWEEN', 'EXISTS', 'IN', 'LIKE', 'SOME',
                    'ASC', 'DESC', 'LIMIT',
                    'DISTINCT', 'GROUP BY', 'HAVING', 'ORDER BY',
                    'IS', 'NOT', 'NULL',
                    ]
                )),
                'font': QFont.Bold,
                'color': palette.color(QPalette.Highlight), # default: Qt.darkBlue
            },
            {
                # Strings simple quotes '...'
                'pattern': "\'.*\'",
                'color': Qt.red,
                'minimal': True, # Need to stop match as soon as possible
            },
            {
                # Strings double quotes: "..."
                'pattern': '\".*\"',
                'color': Qt.red,
                'minimal': True, # Need to stop match as soon as possible
            },
            {
                # Numbers
                'pattern': "\\b[-+]?[0-9]*\.?[0-9]+([eE][-+]?[0-9]+)?\\b",
                'color': Qt.darkGreen,
            },
            {
                # Comments
                'pattern': "--[^\n]*",
                'color': Qt.gray,
            },
        ]

        self.highlighting_rules = list()

        for pattern in self.highlighting_patterns:

            t_format = QTextCharFormat()
            font = pattern.get('font', None)
            if font:
                t_format.setFontWeight(font)

            color = pattern.get('color', None)
            if color:
                t_format.setForeground(color)

            regex = QRegularExpression(pattern['pattern'])
            minimal = pattern.get('minimal', False)
            if minimal:
                # The greediness of the quantifiers is inverted: *, +, ?, {m,n}, etc.
                # become lazy, while their lazy versions (*?, +?, ??, {m,n}?, etc.)
                # become greedy.
                # https://doc.qt.io/Qt-5/qregularexpression.html#setPatternOptions
                regex.setPatternOptions(QRegularExpression.InvertedGreedinessOption)

            self.highlighting_rules.append((regex, t_format))

    def highlightBlock(self, text):
        """override"""

        for regex, t_format in self.highlighting_rules:
            # Ugly iterator => not iterable in Python...
            matchIterator = regex.globalMatch(text)
            while matchIterator.hasNext():
                match = matchIterator.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), t_format)


class VqlEditor(AbstractQueryWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(self.tr("Columns"))
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
