# Standard imports
import os
import tempfile
# Qt imports
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
    QDialog,
    QPushButton,
    QInputDialog,
)
from PySide2.QtCore import QStringListModel, QSize, QDir
# Custom imports
from cutevariant.gui.plugin import PluginWidget
from cutevariant.core.sql import get_sql_connexion, get_sets, get_words_set
from cutevariant.core.command import import_cmd, drop_cmd
from cutevariant import commons as cm
from cutevariant.gui.ficon import FIcon

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
        """Allow to manually add a word to the list

        Notes:
            A user must click on save for the changes to take effect.
        """
        data = self.model.stringList()
        data.append(self.tr("<double click to edit>"))
        self.model.setStringList(data)

    def on_remove(self):
        """Remove the selected rows of the list

        Notes:
            A user must click on save for the changes to take effect.
        """
        while len(self.view.selectionModel().selectedRows()) > 0:
            indexes = self.view.selectionModel().selectedRows()
            self.model.removeRows(indexes[0].row(), 1)

    def on_load_file(self):
        """Allow to automatically add words from a file

        See Also:
            :meth:`load_file`
        """
        # Reload last directory used
        last_directory = self.app_settings.value("last_directory", QDir.homePath())

        filepath, _ = QFileDialog.getOpenFileName(
            self,
            self.tr("Open Word set"),
            last_directory,
            self.tr("Text file (*.txt)"),
        )

        if filepath:
            self.load_file()

    def load_file(self, filename: str):
        """Load file into the view

        A simple file with a list a word

        TODO : Do some Check as @ysard suggest

        Args:
            filename (str): a text file
        """
        if os.path.exists(filename):
            data = []
            with open(filename, "r") as file:
                for line in file:
                    line = line.strip()
                    data.append(str(line))

            self.model.setStringList(data)


class WordSetWidget(PluginWidget):
    """Plugin to show handle gene/word sets from user and gather matching variants
    as a new selection.

    """

    ENABLE = True

    def __init__(self, parent=None):
        super().__init__(parent)
        self.conn = None
        self.setWindowTitle(self.tr("Word Sets"))
        self.toolbar = QToolBar()
        self.view = QListWidget()
        self.view.setIconSize(QSize(20, 20))
        self.view.itemDoubleClicked.connect(self.open_wordset)
        self.view.setSelectionMode(QAbstractItemView.ExtendedSelection)

        # setup tool bar
        self.toolbar.setIconSize(QSize(16, 16))
        self.toolbar.addAction(FIcon(0xF0415), self.tr("Add Word set"), self.add_wordset)
        self.toolbar.addAction(FIcon(0xF0A7A), self.tr("Remove Word set"), self.remove_wordset)

        v_layout = QVBoxLayout()
        v_layout.setContentsMargins(0, 0, 0, 0)
        v_layout.setSpacing(0)

        v_layout.addWidget(self.view)
        v_layout.addWidget(self.toolbar)

        self.setLayout(v_layout)

    def import_wordset(self, words, wordset_name):
        """Import given words into a new wordset in database

        TODO: There is NO CHECK on users inputs!

        Args:
            words(list): List of words to be inserted
            wordset_name(str): Name of the word set

        Returns:
            (boolean): Status of the wordset creation
        """
        # Dump the list in a temporary file
        _, filename = tempfile.mkstemp()
        with open(filename, "w") as file:
            [file.write(word + "\n") for word in words]

        # Import the content of the temp file in DB
        result = import_cmd(self.conn, "sets", wordset_name, filename)

        if not result["success"]:
            LOGGER.error(result)
            QMessageBox.critical(
                self,
                self.tr("Error while importing set"),
                self.tr("Error while importing set '%s'") % wordset_name,
            )
        return result["success"]

    def add_wordset(self):
        """Display a window to allow to add/edit/remove word sets

        The set is then imported in database.
        """
        dialog = WordListDialog()

        if dialog.exec_() == QDialog.Accepted:
            wordset_name, _ = QInputDialog.getText(
                self,
                self.tr("Create a new set"),
                self.tr("Name of the new set:")
            )
            if wordset_name:
                self.import_wordset(dialog.model.stringList(), wordset_name)
                self.populate()

    def remove_wordset(self):
        """Delete word set from database"""
        if len(self.view.selectedItems()) == 0:
            # if selection is empty
            return

        reply = QMessageBox.question(
            self,
            self.tr("Drop word set"),
            self.tr("Are you sure you want to remove the selected set(s)?"),
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        # Delete all selected sets
        for i in self.view.selectedItems():
            result = drop_cmd(self.conn, "sets", i.text())

            if not result["success"]:
                LOGGER.error(result)
                QMessageBox.critical(
                    self,
                    self.tr("Error while deleting set"),
                    self.tr("Error while deleting set '%s'") % i.text(),
                )

        self.populate()

    def open_wordset(self):
        """Display a window to allow to edit the selected word set

        The previous set is dropped and the new is then imported in database.
        """
        wordset_name = self.view.currentItem().text()
        dialog = WordListDialog()

        # populate dialog
        dialog.model.setStringList(list(get_words_set(self.conn, wordset_name)))

        if dialog.exec_() == QDialog.Accepted:
            # Drop previous
            drop_cmd(self.conn, "sets", wordset_name)
            # Import new
            self.import_wordset(dialog.model.stringList(), wordset_name)
            self.populate()

    def on_open_project(self, conn):
        """ override """
        self.conn = conn
        self.on_refresh()

    def on_refresh(self):
        """ override """
        self.populate()

    def populate(self):
        """Actualize the list of word sets"""
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
