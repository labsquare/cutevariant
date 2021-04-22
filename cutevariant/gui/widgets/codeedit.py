from PySide2.QtWidgets import (
    QWidget,
    QTextEdit,
    QApplication,
    QListView,
    QAbstractItemView,
    QLabel,
    QHBoxLayout,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QFrame,
    QStyle,
)
from PySide2.QtGui import (
    QPainter,
    QTextCursor,
    QIcon,
    QPalette,
    QPen,
    QColor,
    QFont,
    QFontMetrics,
    QSyntaxHighlighter,
    QTextCharFormat,
)
from PySide2.QtCore import (
    Qt,
    QSize,
    QStringListModel,
    QSortFilterProxyModel,
    QItemSelectionModel,
    QModelIndex,
    QEvent,
    QObject,
    QAbstractListModel,
    QRect,
    Signal,
    QRegularExpression,
)
import sys

import re


class VqlSyntaxHighlighter(QSyntaxHighlighter):
    """SQL Syntax highlighter for VqlEditor"""

    sql_keywords = (
        "SELECT",
        "FROM",
        "WHERE",
        "AS",
        "AND",
        "OR",
        "NOT",
        "CREATE",
        "DROP",
        "IN",
        "LIKE",
        "GROUP BY",
        "HAVING",
        "HAS",
        "IS",
        "NULL",
        "COUNT",
        "IMPORT",
        "WORDSET",
        "INTERSECT",
    )

    def __init__(self, document=None):
        super().__init__(document)

        palette = QApplication.instance().palette("QTextEdit")

        # SQL Syntax highlighter rules
        # dict: pattern, font, color, minimal (not greedy)
        #  TODO : What about dark mode ?
        self.highlighting_patterns = [
            {
                # Keywords
                # \b allows to perform a "whole words only"
                "pattern": "|".join(
                    (
                        "\\b%s\\b" % keyword
                        for keyword in VqlSyntaxHighlighter.sql_keywords
                    )
                ),
                "font": QFont.Bold,
                "color": palette.color(QPalette.Highlight),  # default: Qt.darkBlue
                "case_insensitive": True,
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
            if pattern.get("minimal", False):
                # The greediness of the quantifiers is inverted: *, +, ?, {m,n}, etc.
                # become lazy, while their lazy versions (*?, +?, ??, {m,n}?, etc.)
                # become greedy.
                # https://doc.qt.io/Qt-5/qregularexpression.html#setPatternOptions
                regex.setPatternOptions(QRegularExpression.InvertedGreedinessOption)

            if pattern.get("case_insensitive", False):
                # NOTE: Deletes previous pattern options
                # Not serious in practice, this only concerns the keywords
                regex.setPatternOptions(QRegularExpression.CaseInsensitiveOption)

            self.highlighting_rules.append((regex, t_format))

    def highlightBlock(self, text):
        """Overrided"""
        for regex, t_format in self.highlighting_rules:
            # Ugly iterator => not iterable in Python...
            matchIterator = regex.globalMatch(text)

            while matchIterator.hasNext():
                match = matchIterator.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), t_format)


class CompleterModel(QAbstractListModel):

    """Model used by Completer which contains keyword name, description, icon and color
    Use add_item to add new items .
    Exemples:

        model.beginResetModel()
        model.add_item("keyword", "description", QIcon(), "white")
        model.add_item("keyword", "description", QIcon(), "white")
        model.add_item("keyword", "description", QIcon(), "white")
        model.endResetModel()

    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self._items = []

    def clear(self):
        """Clear model"""
        self.beginResetModel()
        self._items.clear()
        self.endResetModel()

    def add_item(self, name: str, description: str, icon=QIcon(), color=None):
        """Add items

        Todo:
            Create a signal with beginInsert

        Args:
            name (str): keyword name to be inserted
            description (str): a description of the keyword
            icon (TYPE, optional): the icon
            color (None, optional): the background color icon
        """
        self._items.append(
            {"name": name, "description": description, "icon": icon, "color": color}
        )

    def rowCount(self, parent=QModelIndex()) -> int:
        """Override from QAbstractListModel

        Args:
            parent (QModelIndex, optional)

        Returns:
            int: row count
        """
        if parent == QModelIndex():
            return len(self._items)
        return 0

    def data(self, index: QModelIndex, role: Qt.ItemDataRole):
        """Override from QAbstractListModel

        Args:
            index (QModelIndex): index
            role (Qt.ItemDataRole): role

        Returns:
            Any: value
        """
        if not index.isValid():
            return None

        if role == Qt.DisplayRole:
            return self._items[index.row()]["name"]

        if role == Qt.ToolTipRole:
            return self._items[index.row()]["description"]

        if role == Qt.DecorationRole:
            return self._items[index.row()]["icon"]

        if role == Qt.BackgroundColorRole:
            return QColor(self._items[index.row()]["color"])

        return None


class CompleterDelegate(QStyledItemDelegate):

    """CompleterDelegate is use by the completer to draw nicely icon and elements of the completer"""

    def paint(
        self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex
    ):
        """Paint a cell according index and option

        Args:
            painter (QPainter)
            option (QStyleOptionViewItem)
            index (QModelIndex)
        """

        # Draw background selections
        if option.state & QStyle.State_Selected:
            select_color = option.palette.color(QPalette.Normal, QPalette.Highlight)
            text_color = option.palette.color(QPalette.Normal, QPalette.BrightText)
            painter.fillRect(option.rect, select_color)

        else:
            text_color = option.palette.color(QPalette.Normal, QPalette.Text)

        # get icon and color background
        icon = index.data(Qt.DecorationRole)
        icon_color = index.data(Qt.BackgroundColorRole)

        # draw icon background
        area = QRect(
            option.rect.x(), option.rect.y(), option.rect.height(), option.rect.height()
        )
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(icon_color))
        painter.drawRect(area)

        # Draw icon
        if icon:
            icon_area = area.adjusted(3, 3, -3, -3)
            painter.drawPixmap(icon_area, icon.pixmap(icon_area.size()))

        # Draw text
        text_rect = option.rect
        text_rect.setLeft(option.rect.height() + 3)

        light_font = QFont()
        dark_font = QFont()

        word = index.data(Qt.DisplayRole)
        font = QFont("monospace")
        painter.setFont(font)
        painter.setPen(QPen(text_color))
        painter.drawText(text_rect, Qt.AlignLeft | Qt.AlignVCenter, word)

        #  TODO : higlight match text
        # text_rect.setLeft(
        #     text_rect.left()
        #     + QFontMetrics(light_font).size(Qt.TextSingleLine, word).width()
        # )

        # painter.setPen(QPen("gray"))
        # painter.drawText(text_rect, Qt.AlignLeft | Qt.AlignVCenter, word)


class Completer(QWidget):
    """docstring for ClassName

    Attributes:
        delegate (CompleterDelegate): the delegate use by the view
        model (CompleterModel): the model
        proxy_model (QSortFilterProxyModel ): the proxy model used to filter model
        panel (QLabel): The description widget
        view (QListView): the view

    Signals:
        activated (str): return the keyword selected
    """

    activated = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        self._target = None
        self._completion_prefix = ""

        self.setWindowFlag(Qt.Popup)
        self.setFocusPolicy(Qt.NoFocus)

        #  create model
        self.model = CompleterModel()
        self.proxy_model = QSortFilterProxyModel()
        self.proxy_model.setSourceModel(self.model)
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseInsensitive)

        #  create delegate
        self.delegate = CompleterDelegate()
        # create view
        self.view = QListView()
        self.view.setSelectionMode(QAbstractItemView.SingleSelection)
        self.view.setFocusPolicy(Qt.NoFocus)
        self.view.installEventFilter(self)
        self.view.setModel(self.proxy_model)
        self.view.setItemDelegate(self.delegate)
        self.view.setMinimumWidth(200)
        self.view.setUniformItemSizes(True)
        self.view.setSpacing(0)

        self.view.selectionModel().currentRowChanged.connect(self._on_row_changed)
        self.setFocusProxy(self.view)

        #  create panel info
        self.panel = QLabel()
        self.panel.setAlignment(Qt.AlignTop)
        self.panel.setMinimumWidth(300)
        self.panel.setWordWrap(True)
        self.panel.setFrameShape(QFrame.StyledPanel)

        # Create layout
        vlayout = QHBoxLayout()
        vlayout.setContentsMargins(0, 0, 0, 0)
        vlayout.setSpacing(0)
        vlayout.addWidget(self.view)
        vlayout.addWidget(self.panel)
        self.setLayout(vlayout)

    def set_target(self, target):
        """Set CodeEdit

        Args:
            target (CodeEdit): The CodeEdit
        """
        self._target = target
        self.installEventFilter(self._target)

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        """Filter event from CodeEdit and QListView

        Args:
            obj (QObject): Description
            event (QEvent): Description

        Returns:
            bool
        """

        #  Intercept CodeEdit event
        if obj == self._target:
            if event.type() == QEvent.FocusOut:
                # Ignore lost focus!
                return True
            else:
                obj.event(event)
                return True

        # Intercept QListView event
        if obj == self.view:
            #  Redirect event to QTextExit

            if event.type() == QEvent.KeyPress and self._target:

                current = self.view.selectionModel().currentIndex()

                # emit signal when user press return
                if event.key() == Qt.Key_Return:
                    word = current.data()
                    self.activated.emit(word)
                    self.hide()
                    event.ignore()
                    return True

                # use tab to move down/up in the list
                if event.key() == Qt.Key_Tab:
                    if current.row() < self.proxy_model.rowCount() - 1:
                        self.view.setCurrentIndex(
                            self.proxy_model.index(current.row() + 1, 0)
                        )
                if event.key() == Qt.Key_Backtab:
                    if current.row() > 0:
                        self.view.setCurrentIndex(
                            self.proxy_model.index(current.row() - 1, 0)
                        )

                # Route other key event to the target ! This make possible to write text when completer is visible
                self._target.event(event)

        return super().eventFilter(obj, event)

    def complete(self, rect: QRect):
        """Show completer as popup

        Args:
            rect (QRect): the area where to display the completer

        """
        if self.proxy_model.rowCount() == 0:
            self.hide()
            return

        if self._target:
            pos = self._target.mapToGlobal(rect.bottomRight())
            self.move(pos)
            self.setFocus()
            if not self.isVisible():
                width = 400
                # height = self.view.sizeHintForRow(0) * self.proxy_model.rowCount() + 3
                #  HACK.. TODO better !
                # height = min(self._target.height() / 2, height)

                # self.resize(width, height)
                self.adjustSize()
                self.show()

    def set_completion_prefix(self, prefix: str):
        """Set prefix and filter model

        Args:
            prefix (str): A prefix keyword used to filter model
        """
        self.view.clearSelection()
        self._completion_prefix = QRegularExpression.escape(prefix)

        self.proxy_model.setFilterRegularExpression(
            QRegularExpression(
                f"^{ self._completion_prefix}.*",
                QRegularExpression.CaseInsensitiveOption,
            )
        )
        if self.proxy_model.rowCount() > 0:
            self.select_row(0)

    def select_row(self, row: int):
        """Select a row in the model

        Args:
            row (int): a row number
        """
        index = self.proxy_model.index(row, 0)
        self.view.selectionModel().setCurrentIndex(index, QItemSelectionModel.Select)

    def completion_prefix(self) -> str:
        """getter of completion_prefix

        TODO: use getter / setter

        Returns:
            str: Return the completion_prefix
        """
        return self._completion_prefix

    def hide(self):
        """Override from QWidget

        Hide the completer
        """
        self.set_completion_prefix("")
        super().hide()

    def _on_row_changed(self, current: QModelIndex, previous: QModelIndex):
        """Slot received when user select a new item in the list.
        This is used to update the panel

        Args:
            current (QModelIndex): the selection index
            previous (QModelIndex): UNUSED
        """
        description = current.data(Qt.ToolTipRole)
        self.panel.setText(description)


class CodeEdit(QTextEdit):
    """
    A QTextEdit code editor with a custom completer ( not QCompleter) and a VQL syntax Highlighter.
    To make completer available, you should fill it .

    Examples:

        w = CodeEdit()
        w.completer.model.beginResetModel()
        w.completer.model.add_item("SELECT", "a VQL keyword")
        w.completer.model.add_item("SELECT", "a VQL keyword")
        w.completer.model.add_item("SELECT", "a VQL keyword")
        w.completer.model.endResetModel()

        w.show()

    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.completer = Completer()
        self.completer.set_target(self)

        self.syntax = VqlSyntaxHighlighter(self.document())
        self.setAcceptRichText(False)
        font = QFont("monospace")
        self.setFont(font)

        self.resize(800, 400)

        self.completer.activated.connect(self.insert_completion)

        self._ignore_keys = [
            Qt.Key_Return,
            Qt.Key_Enter,
            Qt.Key_Tab,
            Qt.Key_Backtab,
            Qt.Key_Escape,
            Qt.Key_Up,
            Qt.Key_Down,
        ]

    def keyPressEvent(self, event):

        if event.key() in self._ignore_keys and self.completer.isVisible():
            event.ignore()
            return

        rect = self.cursorRect()

        if event.modifiers() == Qt.ControlModifier and event.key() == Qt.Key_Space:
            self.completer.complete(rect)
            return

        super().keyPressEvent(event)

        # Skip modifier event
        has_modifier = event.modifiers() == Qt.ControlModifier
        if has_modifier:
            return

        word = self.text_under_cursor()

        if len(word) == 0:
            self.completer.hide()
            return

        if word != self.completer.completion_prefix() and len(word) >= 1:
            self.completer.set_completion_prefix(word)
            self.completer.complete(rect)

    def text_under_cursor(self) -> str:
        """return text under cursor

        Returns:
            str
        """
        tc = self.textCursor()
        tc.setPosition(0, QTextCursor.KeepAnchor)
        match = re.findall(r"([\w\.]+)$", tc.selectedText())
        return match[0] if match else ""

    def insert_completion(self, completion: str):
        """Replace current word by completion

        Args:
            completion (str)
        """
        tc = self.textCursor()
        extra = len(self.completer.completion_prefix())
        text_under_cursor = self.text_under_cursor()
        tc.movePosition(
            QTextCursor.Left, QTextCursor.KeepAnchor, len(text_under_cursor)
        )

        tc.removeSelectedText()
        # tc.movePosition(QTextCursor.Left)
        # tc.movePosition(QTextCursor.StartOfWord)
        tc.insertText(completion + " ")


if __name__ == "__main__":
    app = QApplication(sys.argv)

    w = CodeEdit()
    w.completer.model.beginResetModel()
    w.completer.model.add_item("keyword", "description", QIcon(), "white")
    w.completer.model.add_item("keyword", "description", QIcon(), "white")
    w.completer.model.add_item("keyword", "description", QIcon(), "white")
    w.completer.model.endResetModel()

    w.show()

    app.exec_()
