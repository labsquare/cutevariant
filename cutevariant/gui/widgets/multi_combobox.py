from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *


class MultiComboBox(QComboBox):

    # Subclass Delegate to increase item height
    class Delegate(QStyledItemDelegate):
        def sizeHint(self, option, index):
            size = super().sizeHint(option, index)
            size.setHeight(20)
            return size

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Make the combo editable to set a custom text, but readonly
        self.setEditable(True)
        self.lineEdit().setReadOnly(True)
        self.do_not_update_text = False
        # Make the lineedit the same color as QPushButton
        palette = self.palette()
        palette.setBrush(QPalette.Base, palette.button())
        self.lineEdit().setPalette(palette)

        # Use custom delegate
        self.setItemDelegate(MultiComboBox.Delegate())

        # Update the text when an item is toggled
        self.model().dataChanged.connect(self.updateText)

        # Hide and show popup when clicking the line edit
        self.lineEdit().installEventFilter(self)
        self.closeOnLineEditClick = False

        # Prevent popup from closing when clicking on an item
        self.view().viewport().installEventFilter(self)

    def resizeEvent(self, event):
        # Recompute text to elide as needed
        self.updateText()
        super().resizeEvent(event)

    def text(self) -> str:
        return self.lineEdit().text()

    def set_text(self, text: str):
        # Add items
        texts = list(set(text.split(",")))
        for text in texts:
            if not text:
                continue
            item = self.find_words(text)
            if item is None:
                item = self.addItem(text)

            item.setCheckState(Qt.Checked)

        self.updateText()

    def eventFilter(self, object, event):

        if object == self.lineEdit():
            if event.type() == QEvent.MouseButtonRelease:
                if self.closeOnLineEditClick:
                    self.hidePopup()
                else:
                    self.showPopup()
                return True
            return False

        if object == self.view().viewport():
            if event.type() == QEvent.MouseButtonRelease:
                index = self.view().indexAt(event.pos())
                item = self.model().item(index.row())

                if item.checkState() == Qt.Checked:
                    item.setCheckState(Qt.Unchecked)
                else:
                    item.setCheckState(Qt.Checked)
                return True
        return False

    def showPopup(self):
        super().showPopup()
        # When the popup is displayed, a click on the lineedit should close it
        self.closeOnLineEditClick = True

    def hidePopup(self):
        super().hidePopup()
        # Used to prevent immediate reopening when clicking on the lineEdit
        self.startTimer(100)
        # Refresh the display text when closing
        self.updateText()

    def timerEvent(self, event):
        # After timeout, kill timer, and reenable click on line edit
        self.killTimer(event.timerId())
        self.closeOnLineEditClick = False

    def updateText(self):

        texts = []
        for i in range(self.model().rowCount()):
            item_text = self.model().item(i).text()
            if self.model().item(i).checkState() == Qt.Checked:
                texts.append(item_text)
            elif item_text in texts:
                texts.remove(item_text)

        # Compute elided text (with "...")
        metrics = QFontMetrics(self.lineEdit().font())
        # elidedText = metrics.elidedText(text, Qt.ElideRight, self.lineEdit().width())
        text = ",".join(list(set(texts)))
        self.lineEdit().setText(text)

    def addItem(self, text, data=None) -> QStandardItem:

        if text in self.words():
            return

        item = QStandardItem()
        item.setText(text)
        if data is None:
            item.setData(text)
        else:
            item.setData(data)
        item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
        item.setData(Qt.Unchecked, Qt.CheckStateRole)

        self.model().appendRow(item)
        return item

    def addItems(self, texts, datalist=None):
        words = self.words()
        for i, text in enumerate(texts):
            try:
                data = datalist[i]
            except (TypeError, IndexError):
                data = None

            if text not in words:
                self.addItem(text, data)

    def currentData(self):
        # Return the list of selected items data
        res = []
        for i in range(self.model().rowCount()):
            if self.model().item(i).checkState() == Qt.Checked:
                res.append(self.model().item(i).data())
        return res

    def words(self) -> list:
        """return list of words"""
        words = []
        for i in range(self.model().rowCount()):
            words.append(self.model().item(i).text())

        return words

    def find_words(self, word: str) -> QStandardItem:

        items = self.model().findItems(word, Qt.MatchExactly)

        if not items:
            return None

        else:
            return items[0]
