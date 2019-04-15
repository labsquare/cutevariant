from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *


from .plugin import QueryPluginWidget
from cutevariant.core import Query
from cutevariant.core import sql

from cutevariant.commons import MIN_COMPLETION_LETTERS, logger

LOGGER = logger()

class VqlSyntaxHighlighter(QSyntaxHighlighter):
    """SQL Syntax highlighter rules"""

    sql_keywords = (
        'SELECT', 'FROM', 'WHERE', 'AS',
        'AND', 'OR', 'NOT', 'ALL', 'ANY', 'BETWEEN', 'EXISTS', 'IN', 'LIKE', 'SOME',
        'ASC', 'DESC', 'LIMIT',
        'DISTINCT', 'GROUP BY', 'HAVING', 'ORDER BY',
        'IS', 'NOT', 'NULL',
    )

    def __init__(self, document=None):
        super().__init__(document)

        palette = qApp.palette("QTextEdit")

        # SQL Syntax highlighter rules
        # dict: pattern, font, color, minimal (not greedy)
        #  TODO : What about dark mode ?
        self.highlighting_patterns = [
            {
                # Keywords
                # \b allows to perform a "whole words only"
                "pattern": "|".join(
                    (
                        f"\\b%s\\b" % keyword
                        for keyword in VqlSyntaxHighlighter.sql_keywords
                    )
                ),
                "font": QFont.Bold,
                "color": palette.color(QPalette.Highlight),  # default: Qt.darkBlue
            },
            {
                # Strings simple quotes '...'
                "pattern": r"\'.*\'",
                "color": Qt.red,
                "minimal": True,  # Need to stop match as soon as possible
            },
            {
                # Strings double quotes: "..."
                "pattern": r"\".*\"",
                "color": Qt.red,
                "minimal": True,  # Need to stop match as soon as possible
            },
            {
                # Numbers
                "pattern": r"\\b[-+]?[0-9]*\.?[0-9]+([eE][-+]?[0-9]+)?\\b",
                "color": Qt.darkGreen,
            },
            {
                # Comments
                "pattern": r"--[^\n]*",
                "color": Qt.gray,
            },
        ]

        self.highlighting_rules = list()

        for pattern in self.highlighting_patterns:

            t_format = QTextCharFormat()
            font = pattern.get("font", None)
            if font:
                t_format.setFontWeight(font)

            color = pattern.get("color", None)
            if color:
                t_format.setForeground(color)

            regex = QRegularExpression(pattern["pattern"])
            minimal = pattern.get("minimal", False)
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


class VqlEditor(QueryPluginWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(self.tr("Columns"))

        self.text_edit = VqlEdit()
        self.highlighter = VqlSyntaxHighlighter(self.text_edit.document())
        main_layout = QVBoxLayout()
        main_layout.addWidget(self.text_edit)
        main_layout.setContentsMargins(0,0,0,0)
        self.setLayout(main_layout)
        self.text_edit.textChanged.connect(self.changed)

    def setQuery(self, query: Query):
        """Method override from AbstractQueryWidget"""
        self.query = query
        self.text_edit.setPlainText(self.query.to_vql())

        if self.text_edit.completer is None:
            self.text_edit.setCompleter(self.create_completer())

    def getQuery(self):
        """Method override from AbstractQueryWidget"""
        try:
            self.query.from_vql(self.text_edit.toPlainText())
            return self.query
        except AttributeError:
            LOGGER.debug("VqlEditor:getQuery:: no query attribute")
            return None

    def create_completer(self):
        """Create Completer with his model"""
        model = QStringListModel()
        completer = QCompleter()
        fields = [i["name"] for i in sql.get_fields(self.query.conn)]
        fields.extend(VqlSyntaxHighlighter.sql_keywords)
        model.setStringList(fields)
        completer.setModel(model)
        return completer


class VqlEdit(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.completer = None

    def setCompleter(self, completer: QCompleter):

        if self.completer:
            self.completer.activated.disconnect()

        self.completer = completer
        self.completer.setWidget(self)
        self.completer.setCompletionMode(QCompleter.PopupCompletion)
        self.completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.completer.activated.connect(self.insertCompletion)

    def keyPressEvent(self, event):
        """Overrided"""

        # Ignore some key events so the completer can handle them.
        if self.completer and self.completer.popup().isVisible():
            if event.key() in (
                Qt.Key_Enter,
                Qt.Key_Return,
                Qt.Key_Escape,
                Qt.Key_Tab,
                Qt.Key_Backtab,
            ):
                event.ignore()
                # Let the completer do default behavior
                return

        # Accept other key events
        super().keyPressEvent(event)

        # Ignore modifiers
        found_ignored_modifier = event.modifiers() in (
            Qt.ControlModifier,
            Qt.ShiftModifier,
            Qt.AltModifier,
        )

        LOGGER.debug("keyPressEvent:: event text: %s", event.text())

        # Dismiss ingored modifiers without text
        if not self.completer or (found_ignored_modifier and not event.text()):
            LOGGER.debug("keyPressEvent:: ignored modifier")
            return

        has_modifier = event.modifiers() != Qt.NoModifier and not found_ignored_modifier

        end_of_word = "~!@#$%^&*()_+{}|:\"<>?,./;'[]\\-="
        completion_prefix = self.textUnderCursor()
        completer = self.completer

        LOGGER.debug("keyPressEvent:: has_modifier: %s", has_modifier)
        LOGGER.debug("keyPressEvent:: completion_prefix: %s", completion_prefix)

        # Hide on alone modifier, empty text, short text, end of word
        if (
            has_modifier
            or not event.text()
            or len(completion_prefix) < MIN_COMPLETION_LETTERS
            or event.text()[-1] in end_of_word
        ):
            completer.popup().hide()
            LOGGER.debug("keyPressEvent:: Hide completer popup")
            return

        # Select proposed word
        if completion_prefix != completer.completionPrefix():
            completer.setCompletionPrefix(completion_prefix)
            completer.popup().setCurrentIndex(completer.completionModel().index(0, 0))

        # Show popup
        cursor_rect = self.cursorRect()
        cursor_rect.setWidth(
            completer.popup().sizeHintForColumn(0)
            + completer.popup().verticalScrollBar().sizeHint().width()
        )
        completer.complete(cursor_rect)

    def focusInEvent(self, event):
        """Overrided: Event handler used to receive keyboard focus events for the widget"""
        if self.completer:
            self.completer.setWidget(self)

        super().focusInEvent(event)

    def insertCompletion(self, completion: str):
        """Complete the word using the given completion string

        .. note:: Called after user validation in the popup

        :param completion: Word proposed by the autocompletion.
        :type completion: <str>
        """

        # Ensure that the completer's widget is the current one
        if self.completer.widget() != self:
            return

        tc = self.textCursor()
        # Get number of characters that must be inserted
        # The last nb_extra characters from the right will be inserted by tc
        nb_extra = len(completion) - len(self.completer.completionPrefix())
        # Do not replace anything if the word is already completed
        # => avoid word duplication when the cursor is not moved (nb_extra = 0)
        if nb_extra == 0:
            return

        tc.movePosition(QTextCursor.Left)  # left one character.
        tc.movePosition(QTextCursor.EndOfWord)  # end of the current word.
        # Get a substring that contains the nb_extra rightmost characters
        # of the string; and insert the extra characters to complete the word.
        tc.insertText(completion[-nb_extra:])
        self.setTextCursor(tc)

    def textUnderCursor(self):
        """Select a word under the cursor and return it

        :return: The text/fragment of word under the cursor.
        :rtype: <QTextCursor>
        """

        tc = self.textCursor()
        tc.select(QTextCursor.WordUnderCursor)
        return tc.selectedText()
