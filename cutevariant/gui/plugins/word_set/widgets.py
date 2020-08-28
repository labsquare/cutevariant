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
    QFileDialog,
    QMessageBox,
    QDialog,
    QPushButton,
)


from PySide2.QtCore import QStringListModel

LOGGER = cm.logger()


class WordSetWidget(PluginWidget):
    """Plugin to show all annotations of a selected variant"""

    ENABLE = True

    def __init__(self, conn=None):
        super().__init__()
        self.conn = conn
        self.setWindowTitle(self.tr("Word Set"))
        self.toolbar = QToolBar()
        self.view = QListWidget()
        self.view.setIconSize(QSize(20, 20))
        self.view.itemDoubleClicked.connect(self.open_wordset)

        # setup tool bar
        self.toolbar.setIconSize(QSize(16, 16))
        self.toolbar.addAction(FIcon(0xF0415), "Add", self.add_wordset)
        self.toolbar.addAction(FIcon(0xF0A7A), "Rem", self.rem_wordset)
        self.toolbar.addAction(FIcon(0xF06D0), "open", self.open_wordset)

        v_layout = QVBoxLayout()
        v_layout.setContentsMargins(0, 0, 0, 0)
        v_layout.setSpacing(0)

        v_layout.addWidget(self.view)
        v_layout.addWidget(self.toolbar)

        self.setLayout(v_layout)

    def add_wordset(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, "Open word set", "", "Text File (*.txt)"
        )

        if filename:
            name = os.path.basename(filename)
            result = import_cmd(self.conn, "sets", name, filename)
            LOGGER.debug(result)
            self.populate()

    def rem_wordset(self):

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

        if len(self.view.selectedItems()) == 0:
            return

        set_name = self.view.selectedItems()[0].text()

        dialog = QDialog()
        view = QListView()
        model = QStringListModel()
        view.setModel(model)
        view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        button = QPushButton("OK")
        vlayout = QVBoxLayout()
        vlayout.addWidget(view)
        vlayout.addWidget(button)
        dialog.setLayout(vlayout)
        dialog.setWindowTitle(set_name)

        # Load word sets

        model.setStringList(get_words_set(self.conn, set_name))
        button.clicked.connect(dialog.accept)

        dialog.exec_()

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

    conn = get_sql_connexion("test.db")

    import_cmd(conn, "sets", "boby", "examples/gene.txt")

    w = WordSetWidget()
    w.conn = conn

    w.populate()

    w.show()

    app.exec_()
