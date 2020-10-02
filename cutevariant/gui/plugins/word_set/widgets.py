from cutevariant.gui.plugin import PluginWidget
from cutevariant.core.sql import get_sql_connexion, get_sets, get_words_set
from cutevariant.core.command import import_cmd, import_cmd, drop_cmd
from cutevariant import commons as cm
from cutevariant.gui.ficon import FIcon

import os
from PySide2.QtWidgets import (
    QToolBar,
    QListWidget,
    QListView,
    QAbstractItemView,
    QListWidgetItem,
    QVBoxLayout,
    QHBoxLayout,
    QFileDialog,
    QMessageBox,
    QDialogButtonBox,
    QDialog,
    QPushButton,
    QInputDialog,
)


from PySide2.QtCore import QStringListModel, Qt, QDir, QSize
from PySide2.QtGui import QIcon

import tempfile


LOGGER = cm.logger()


class WordListDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        box = QVBoxLayout()
        self.add_button = QPushButton("Add")
        self.del_button = QPushButton("Remove")
        self.add_file_button = QPushButton("From file ...")

        self.save_button = QPushButton("Save")
        self.cancel_button = QPushButton("Cancel")

        box.addWidget(self.add_button)
        box.addWidget(self.del_button)
        box.addWidget(self.add_file_button)
        box.addStretch()
        box.addWidget(self.save_button)
        box.addWidget(self.cancel_button)

        self.view = QListView()
        self.model = QStringListModel()
        self.view.setModel(self.model)
        self.view.setSelectionMode(QAbstractItemView.ContiguousSelection)

        hlayout = QHBoxLayout()
        hlayout.addWidget(self.view)
        hlayout.addLayout(box)

        self.setLayout(hlayout)

        self.add_button.pressed.connect(self.on_add)
        self.del_button.pressed.connect(self.on_remove)
        self.add_file_button.pressed.connect(self.on_load_file)

        self.cancel_button.pressed.connect(self.reject)
        self.save_button.pressed.connect(self.accept)

    def on_add(self):
        data = self.model.stringList()
        data.append("<double click to edit>")
        self.model.setStringList(data)

    def on_remove(self):

        while len(self.view.selectionModel().selectedRows()) > 0:
            indexes = self.view.selectionModel().selectedRows()
            self.model.removeRows(indexes[0].row(), 1)

    def on_load_file(self):

        filename, _ = QFileDialog.getOpenFileName(self, "file", "", "Text file (*.txt)")

        if filename:
            data = []
            with open(filename, "r") as file:
                for line in file:
                    line = line.strip()
                    data.append(str(line))

            self.model.setStringList(data)


class WordSetWidget(PluginWidget):
    """Plugin to show all annotations of a selected variant"""

    ENABLE = True

    def __init__(self, parent=None):
        super().__init__(parent)
        self.conn = None
        self.setWindowTitle(self.tr("Word Set"))
        self.toolbar = QToolBar()
        self.view = QListWidget()
        self.view.setIconSize(QSize(20, 20))
        self.view.itemDoubleClicked.connect(self.open_wordset)

        # setup tool bar
        self.toolbar.setIconSize(QSize(16, 16))
        self.toolbar.addAction(FIcon(0xF0415), "Add", self.add_wordset)
        self.toolbar.addAction(FIcon(0xF0A7A), "Remove", self.remove_wordset)

        v_layout = QVBoxLayout()
        v_layout.setContentsMargins(0, 0, 0, 0)
        v_layout.setSpacing(0)

        v_layout.addWidget(self.view)
        v_layout.addWidget(self.toolbar)

        self.setLayout(v_layout)

    def add_wordset(self):

        dialog = WordListDialog()

        if dialog.exec_() == QDialog.Accepted:
            name, _ = QInputDialog.getText(self, "Set name", "Set name")
            if name:
                _, filename = tempfile.mkstemp()
                with open(filename, "w") as file:
                    for word in dialog.model.stringList():
                        file.write(word + "\n")

                import_cmd(self.conn, "sets", name, filename)
                self.populate()

    def remove_wordset(self):

        # if selection is empty
        if len(self.view.selectedItems()) == 0:
            return

        reply = QMessageBox.question(
            self,
            "Drop word set",
            "Are you sure you want to remove selected elements ?",
            QMessageBox.Yes | QMessageBox.No,
        )
        print(reply)
        if reply == QMessageBox.Yes:
            for i in self.view.selectedItems():
                result = drop_cmd(self.conn, "sets", i.text())
                LOGGER.debug(result)

            self.populate()

    def open_wordset(self):

        name = self.view.currentItem().text()
        dialog = WordListDialog()

        # populate dialog
        dialog.model.setStringList(list(get_words_set(self.conn, name)))

        if dialog.exec_() == QDialog.Accepted:
            #  Drop previous
            drop_cmd(self.conn, "sets", name)
            _, filename = tempfile.mkstemp()
            with open(filename, "w") as file:
                for word in dialog.model.stringList():
                    file.write(word + "\n")

            import_cmd(self.conn, "sets", name, filename)
            self.populate()

    def on_open_project(self, conn):
        """ override """
        self.conn = conn
        self.on_refresh()

    def on_refresh(self):
        """ override """
        self.populate()

    def populate(self):
        self.view.clear()
        for data in get_sets(self.conn):
            item = QListWidgetItem()
            item.setText(data["name"])
            item.setIcon(FIcon(0xF0A38))
            self.view.addItem(item)


if __name__ == "__main__":
    import sys
    from PySide2.QtWidgets import QApplication

    app = QApplication(sys.argv)

    conn = get_sql_connexion("C:/sacha/Dev/cutevariant/test.db")

    # import_cmd(conn, "sets", "boby", "examples/gene.txt")

    w = WordSetWidget()
    w.conn = conn

    w.populate()

    w.show()

    app.exec_()
