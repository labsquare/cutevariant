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
from PySide2.QtCore import QStringListModel, QSize, QDir, QSettings
from PySide2.QtGui import QIcon

# Custom imports
from cutevariant.gui.plugin import PluginWidget
from cutevariant.core.sql import (
    get_sql_connection,
    get_wordsets,
    get_words_in_set,
    sanitize_words,
)
from cutevariant.core.command import import_cmd, drop_cmd
from cutevariant import commons as cm
from cutevariant.gui.ficon import FIcon

LOGGER = cm.logger()


class WordListDialog(QDialog):
    """Window to handle the edition of words in a word set"""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle(self.tr("Edit Word set"))
        self.setWindowIcon(QIcon(cm.DIR_ICONS + "app.png"))

        box = QVBoxLayout()
        self.add_button = QPushButton(self.tr("Add"))
        self.add_file_button = QPushButton(self.tr("Add from file..."))
        self.del_button = QPushButton(self.tr("Remove"))
        self.del_button.setDisabled(True)

        self.save_button = QPushButton(self.tr("Save"))
        self.save_button.setDisabled(True)
        self.cancel_button = QPushButton(self.tr("Cancel"))

        box.addWidget(self.add_button)
        box.addWidget(self.del_button)
        box.addWidget(self.add_file_button)
        box.addStretch()
        box.addWidget(self.save_button)
        box.addWidget(self.cancel_button)

        self.view = QListView()
        self.model = QStringListModel()
        self.view.setModel(self.model)
        self.view.setSelectionMode(QAbstractItemView.ExtendedSelection)

        hlayout = QHBoxLayout()
        hlayout.addWidget(self.view)
        hlayout.addLayout(box)

        self.setLayout(hlayout)

        self.add_button.pressed.connect(self.on_add)
        self.del_button.pressed.connect(self.on_remove)
        self.add_file_button.pressed.connect(self.on_load_file)

        self.cancel_button.pressed.connect(self.reject)
        self.save_button.pressed.connect(self.accept)
        # Item selected in view
        self.view.selectionModel().selectionChanged.connect(self.on_item_selected)
        # Data changed in model
        self.model.dataChanged.connect(self.on_data_changed)
        self.model.rowsInserted.connect(self.on_data_changed)
        self.model.rowsRemoved.connect(self.on_data_changed)

    def on_item_selected(self, *args):
        """Enable the remove button when an item is selected"""
        self.del_button.setEnabled(True)

    def on_data_changed(self, *args):
        """Enable the save button when data in model is changed"""
        self.save_button.setEnabled(True)

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
        indexes = self.view.selectionModel().selectedRows()
        while indexes:
            self.model.removeRows(indexes[0].row(), 1)
            indexes = self.view.selectionModel().selectedRows()

        self.del_button.setDisabled(True)

    def on_load_file(self):
        """Allow to automatically add words from a file

        See Also:
            :meth:`load_file`
        """
        # Reload last directory used
        last_directory = QSettings().value("last_directory", QDir.homePath())

        filepath, _ = QFileDialog.getOpenFileName(
            self, self.tr("Open Word set"), last_directory, self.tr("Text file (*.txt)")
        )

        if filepath:
            self.load_file(filepath)

    def load_file(self, filename: str):
        """Load file into the view

        Args:
            filename(str): A simple file with a list of words (1 per line)

        Current data filtering:
            - Strip trailing spaces and EOL characters
            - Skip empty lines
            - Skip lines with whitespaces characters (`[ \t\n\r\f\v]`)

        Examples:
            - The following line will be skipped:
            `"abc  def\tghi\t  \r\n"`
            - The following line will be cleaned:
            `"abc\r\n"`
        """
        if not os.path.exists(filename):
            return

        # Sanitize words
        with open(filename, "r") as f_h:
            data = sanitize_words(f_h)

        data.update(self.model.stringList())
        self.model.setStringList(list(data))
        # Simulate signal... TODO: check the syntax...
        self.model.rowsInserted.emit(0, 0, 0)


class WordSetWidget(PluginWidget):
    """Plugin to show handle word sets from user and gather matching variants
    as a new selection.
    """

    ENABLE = True

    def __init__(self, parent=None):
        super().__init__(parent)
        self.conn = None
        self.set_names = list()
        self.setWindowTitle(self.tr("Word Sets"))
        self.toolbar = QToolBar()
        self.view = QListWidget()
        self.view.setIconSize(QSize(20, 20))
        self.view.itemDoubleClicked.connect(self.open_wordset)
        self.view.setSelectionMode(QAbstractItemView.ExtendedSelection)

        # setup tool bar
        self.toolbar.setIconSize(QSize(16, 16))
        self.toolbar.addAction(
            FIcon(0xF0415), self.tr("Add Word set"), self.add_wordset
        )
        self.edit_action = self.toolbar.addAction(
            FIcon(0xF0DC9), self.tr("Edit Word set"), self.open_wordset
        )
        self.remove_action = self.toolbar.addAction(
            FIcon(0xF0A7A), self.tr("Remove Word set"), self.remove_wordset
        )
        self.edit_action.setEnabled(False)
        self.remove_action.setEnabled(False)

        v_layout = QVBoxLayout()
        v_layout.setContentsMargins(0, 0, 0, 0)
        v_layout.setSpacing(0)

        v_layout.addWidget(self.view)
        v_layout.addWidget(self.toolbar)

        self.setLayout(v_layout)

        # Item selected in view
        self.view.selectionModel().selectionChanged.connect(self.on_item_selected)

    def on_item_selected(self, *args):
        """Enable the remove button when an item is selected"""
        # Get list of all selected model item indexes
        if self.view.selectionModel().selectedIndexes():
            self.edit_action.setEnabled(True)
            self.remove_action.setEnabled(True)
        else:
            self.edit_action.setEnabled(False)
            self.remove_action.setEnabled(False)

    def import_wordset(self, words, wordset_name):
        """Import given words into a new wordset in database

        Warnings:
            There is NO CHECK on manual user's inputs! Except during DB insertion.

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
        result = import_cmd(self.conn, "wordsets", wordset_name, filename)

        if not result["success"]:
            LOGGER.error(result)
            QMessageBox.critical(
                self,
                self.tr("Error while importing set"),
                self.tr("Error while importing set '%s'") % wordset_name,
            )

        os.remove(filename)
        return result["success"]

    def add_wordset(self):
        """Display a window to allow to add/edit/remove word sets

        The set is then imported in database.
        """
        dialog = WordListDialog()

        if dialog.exec_() != QDialog.Accepted:
            return

        wordset_name = None
        while not wordset_name:
            wordset_name, _ = QInputDialog.getText(
                self, self.tr("Create a new set"), self.tr("Name of the new set:")
            )
            if not wordset_name:
                return

            if wordset_name in self.set_names:
                # Name already used
                QMessageBox.critical(
                    self,
                    self.tr("Error while creating set"),
                    self.tr("Error while creating set '%s'; Name is already used")
                    % wordset_name,
                )
                wordset_name = None

        # Import & update view
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
            result = drop_cmd(self.conn, "wordsets", i.text())

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
        dialog.model.setStringList(list(get_words_in_set(self.conn, wordset_name)))

        if dialog.exec_() == QDialog.Accepted:
            # Drop previous
            drop_cmd(self.conn, "wordsets", wordset_name)
            # Import new
            self.import_wordset(dialog.model.stringList(), wordset_name)
            self.populate()

    def on_open_project(self, conn):
        """ override """
        self.conn = conn
        self.on_refresh()

    def on_refresh(self):
        """ override """
        if self.conn:
            self.populate()

    def populate(self):
        """Actualize the list of word sets"""
        self.view.clear()
        self.set_names = list()
        for data in get_wordsets(self.conn):
            set_name = data["name"]
            item = QListWidgetItem()
            item.setText(set_name)
            item.setIcon(FIcon(0xF0A38))
            self.view.addItem(item)
            self.set_names.append(set_name)


if __name__ == "__main__":
    import sys
    from PySide2.QtWidgets import QApplication

    app = QApplication(sys.argv)

    conn = get_sql_connection("C:/sacha/Dev/cutevariant/test.db")

    # import_cmd(conn, "sets", "boby", "examples/gene.txt")
    w = WordSetWidget()
    w.conn = conn
    w.populate()
    w.show()
    app.exec_()
