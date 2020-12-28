from PySide2.QtWidgets import (
    QWidget,
    QTextEdit,
    QApplication,
    QListView,
    QAbstractItemView,
    QLabel,
    QHBoxLayout,
)
from PySide2.QtGui import QPainter, QTextCursor, QIcon
from PySide2.QtCore import (
    Qt,
    QStringListModel,
    QSortFilterProxyModel,
    QItemSelectionModel,
    QModelIndex,
    QEvent,
    QObject,
    QAbstractListModel,
    QRect,
    Signal,
)
import sys

from cutevariant.gui import FIcon, setFontPath


class CompleterModel(QAbstractListModel):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.items = [
            {
                "name": "SELECT",
                "description": "POUR FAIRE UNE SELECTION",
                "icon": 0xF03AD,
            },
            {"name": "chr", "description": "chromosome", "icon": 0xF03AD},
            {"name": "chrisalide", "description": "chrisalide", "icon": 0xF03AD},
            {"name": "chrosss", "description": "chrosss", "icon": 0xF03AD},
            {"name": "pos", "description": "position", "icon": 0xF03AD},
        ]

    def rowCount(self, parent=None):
        if parent == QModelIndex():
            return len(self.items)
        return 0

    def data(self, index: QModelIndex, role: Qt.ItemDataRole):

        if not index.isValid():
            return None

        if role == Qt.DisplayRole:
            return self.items[index.row()]["name"]

        if role == Qt.ToolTipRole:
            return self.items[index.row()]["description"]

        if role == Qt.DecorationRole:
            return QIcon(FIcon(0xF14DE))

        return None


class Completer(QWidget):
    """docstring for ClassName"""

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
        # create view
        self.view = QListView()
        self.view.setSelectionMode(QAbstractItemView.SingleSelection)
        self.view.setFocusPolicy(Qt.NoFocus)
        self.view.installEventFilter(self)
        self.view.setModel(self.proxy_model)
        self.view.setMinimumWidth(200)
        self.view.selectionModel().currentRowChanged.connect(self._on_row_changed)
        self.setFocusProxy(self.view)

        #  create panel info
        self.panel = QLabel()
        self.panel.setAlignment(Qt.AlignTop)
        self.panel.setMinimumWidth(200)

        self.panel.setText(
            """
            Impact (str)

            Impact of the variant 
            et ca fait ca 

            exemple: HIGH
            """
        )

        vlayout = QHBoxLayout()
        vlayout.setContentsMargins(0, 0, 0, 0)
        vlayout.addWidget(self.view)
        vlayout.addWidget(self.panel)
        self.setLayout(vlayout)

    def set_target(self, target: QTextEdit):
        self._target = target
        self.installEventFilter(self._target)

    def eventFilter(self, obj: QObject, event: QEvent):

        #  Intercept QTextEdit event
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

                if event.key() == Qt.Key_Return:
                    word = current.data()
                    self.activated.emit(word)
                    self.hide()
                    event.ignore()
                    return True

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

                self._target.event(event)

        return super().eventFilter(obj, event)

    def complete(self, rect: QRect):

        if self.proxy_model.rowCount() == 0:
            self.hide()
            return

        if self._target:
            pos = self._target.mapToGlobal(rect.bottomRight())
            self.move(pos)
            self.setFocus()
            if not self.isVisible():
                width = 400
                height = self.view.sizeHintForRow(0) * self.proxy_model.rowCount() + 3
                self.resize(width, height)
                self.show()

    def set_completion_prefix(self, prefix: str):

        self.view.clearSelection()
        self._completion_prefix = prefix
        self.proxy_model.setFilterWildcard(prefix + "*")
        if self.proxy_model.rowCount() > 0:
            self.select_row(0)

    def select_row(self, row: int):

        index = self.proxy_model.index(row, 0)
        self.view.selectionModel().setCurrentIndex(index, QItemSelectionModel.Select)

    def completion_prefix(self):
        return self._completion_prefix

    def hide(self):
        self.set_completion_prefix("")
        super().hide()

    def _on_row_changed(self, current: QModelIndex, previous: QModelIndex):

        description = previous.data(Qt.ToolTipRole)
        self.panel.setText(description)


class CodeEdit(QTextEdit):
    """docstring for ClassName"""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.completer = Completer()
        self.completer.set_target(self)

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

        word = self.text_under_cursor()

        if len(word) == 0:
            self.completer.hide()
            return

        if word != self.completer.completion_prefix() and len(word) >= 1:
            self.completer.set_completion_prefix(word)
            self.completer.complete(rect)

    def text_under_cursor(self):

        tc = self.textCursor()
        tc.select(QTextCursor.WordUnderCursor)
        return tc.selectedText()

    def insert_completion(self, completion):

        tc = self.textCursor()
        extra = len(self.completer.completion_prefix())

        tc.movePosition(QTextCursor.Left)
        tc.movePosition(QTextCursor.EndOfWord)
        tc.insertText(completion[extra:] + " ")


if __name__ == "__main__":
    app = QApplication(sys.argv)

    setFontPath(
        "/home/sacha/Dev/cutevariant/cutevariant/assets/fonts/materialdesignicons-webfont.ttf"
    )

    w = CodeEdit()
    w.show()

    app.exec_()
