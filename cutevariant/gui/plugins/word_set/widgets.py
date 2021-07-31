# Standard imports
import json
import os
import sqlite3
import tempfile
import typing


# Qt imports

from PySide2.QtWidgets import (
    QLineEdit,
    QTableView,
    QToolBar,
    QListView,
    QAbstractItemView,
    QHeaderView,
    QVBoxLayout,
    QHBoxLayout,
    QFileDialog,
    QMessageBox,
    QDialog,
    QPushButton,
    QLabel,
    QInputDialog,
    QMenu,
)

from PySide2.QtCore import (
    QAbstractTableModel,
    QMimeData,
    QModelIndex,
    QObject,
    QStringListModel,
    QSize,
    QDir,
    QSettings,
    QItemSelectionModel,
    QUrl,
    Qt,
)
from PySide2.QtGui import QIcon, QContextMenuEvent, QKeyEvent, QKeySequence

# Custom imports
from cutevariant.gui.plugin import PluginWidget
from cutevariant.core.sql import (
    get_sql_connection,
    get_wordsets,
    get_words_in_set,
    sanitize_words,
    intersect_wordset,
    union_wordset,
    subtract_wordset,
)
from cutevariant.core.command import import_cmd, drop_cmd
from cutevariant import commons as cm
from cutevariant.gui.ficon import FIcon
from cutevariant.gui.widgets import SearchableTableWidget

from cutevariant import LOGGER


class WordListDialog(QDialog):
    """Window to handle the edition of words in a word set"""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle(self.tr("Edit Word set"))
        self.setWindowIcon(QIcon(cm.DIR_ICONS + "app.png"))

        box = QVBoxLayout()
        self.add_button = QPushButton(FIcon(0xF0415), self.tr("Add"))
        self.paste_file_button = QPushButton(FIcon(0xF0192), self.tr("Paste"))
        self.add_file_button = QPushButton(FIcon(0xF0EED), self.tr("Add from file..."))
        self.del_button = QPushButton(FIcon(0xF0A7A), self.tr("Remove"))
        self.del_button.setDisabled(True)

        self.save_button = QPushButton(self.tr("Save"))
        self.save_button.setDisabled(True)
        self.cancel_button = QPushButton(self.tr("Cancel"))

        box.addWidget(self.add_button)
        box.addWidget(self.paste_file_button)
        box.addWidget(self.add_file_button)
        box.addWidget(self.del_button)
        box.addStretch()
        box.addWidget(self.save_button)
        box.addWidget(self.cancel_button)

        self.view = QListView()
        self.model = QStringListModel()
        self.view.setModel(self.model)
        self.view.setSelectionMode(QAbstractItemView.ExtendedSelection)

        vlayout = QVBoxLayout()
        #  Create title label
        self.title_label = QLabel()
        self.title_label.setText(self.tr("Create a set by adding words"))
        vlayout.addWidget(self.title_label)
        vlayout.addWidget(self.view)

        hlayout = QHBoxLayout()
        hlayout.addLayout(vlayout)
        hlayout.addLayout(box)

        self.setLayout(hlayout)

        self.add_button.pressed.connect(self.on_add)
        self.del_button.pressed.connect(self.on_remove)
        self.add_file_button.pressed.connect(self.on_load_file)
        self.paste_file_button.pressed.connect(self.on_paste)
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

    def on_paste(self):
        text = qApp.clipboard().text()

        words = self.model.stringList()
        for word in text.splitlines():
            words.append(word)

        self.model.setStringList(words)

    def on_add(self):
        """Allow to manually add a word to the list

        Notes:
            A user must click on save for the changes to take effect.
        """
        data = self.model.stringList()
        data.append(self.tr("<double click to edit>"))
        self.model.setStringList(data)
        last_index = self.model.index(len(data) - 1)
        self.view.setCurrentIndex(last_index)
        self.view.edit(last_index)

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


class WordsetCollectionModel(QAbstractTableModel):
    def __init__(self, conn: sqlite3.Connection = None, parent: QObject = None) -> None:
        super().__init__(parent)
        self._raw_data = []
        self.conn = conn

    def data(self, index: QModelIndex, role: int) -> typing.Any:

        if (
            index.row() < 0
            or index.row() >= self.rowCount()
            or index.column() not in (0, 1)
        ):
            return

        if role == Qt.DecorationRole and index.column() == 0:
            return QIcon(FIcon(0xF0A38))

        if role == Qt.TextAlignmentRole and index.column() == 1:
            return Qt.AlignCenter

        if role == Qt.DisplayRole:
            return self._raw_data[index.row()][index.column()]

    def headerData(
        self, section: int, orientation: Qt.Orientation, role: int
    ) -> typing.Any:
        if (
            orientation != Qt.Horizontal
            or section not in (0, 1)
            or role != Qt.DisplayRole
        ):
            return

        if section == 0:
            return self.tr("Wordset name")
        if section == 1:
            return self.tr("Count")

    def load(self):
        if self.conn:
            self._set_dict(
                {data["name"]: data["count"] for data in get_wordsets(self.conn)}
            )

    def _set_dict(self, data: dict):
        self.beginResetModel()
        self._raw_data = [(k, v) for k, v in data.items()]
        self.endResetModel()

    def clear(self):
        self._set_dict({})

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._raw_data)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 2

    def wordset_names(self):
        return list(dict(self._raw_data).keys())

    def mimeData(self, indexes: typing.List) -> QMimeData:
        wordset_names = [
            idx.data(Qt.DisplayRole) for idx in indexes if idx.column() == 0
        ]
        if len(wordset_names) != 1:
            # Currently, we don't support dragging more than one wordset
            return None
        res = QMimeData()
        ser_wordset = wordset_names[0]
        res.setText(json.dumps({"ann.gene": {"$in": {"$wordset": ser_wordset}}}))
        res.setData(
            "cutevariant/typed-json",
            bytes(
                json.dumps(
                    {
                        "type": "condition",
                        "condition": {
                            "field": "ann.gene",
                            "operator": "$in",
                            "value": {"$wordset": ser_wordset},
                        },
                    }
                ),
                "utf-8",
            ),
        )
        return res

    def import_from_file(self, filename: str):

        if not self.conn:
            return False
        wordet_name = os.path.basename(filename).split(".")[0]

        result = import_cmd(self.conn, "wordsets", wordet_name, filename)

        # Load anyway. If there was an error, we still want the model to be valid with existing wordsets
        self.load()

        if not result["success"]:
            LOGGER.error(result)
            QMessageBox.critical(
                self,
                self.tr("Error while importing set"),
                self.tr("Error while importing set '%s'") % filename,
            )
            return False
        return True

    def canDropMimeData(
        self,
        data: QMimeData,
        action: Qt.DropAction,
        row: int,
        column: int,
        parent: QModelIndex,
    ) -> bool:

        if data.hasFormat("text/uri-list") and action == Qt.CopyAction:
            return True
        return False

    def dropMimeData(
        self,
        data: QMimeData,
        action: Qt.DropAction,
        row: int,
        column: int,
        parent: QModelIndex,
    ) -> bool:
        if action == Qt.CopyAction:
            if data.hasFormat("text/uri-list"):
                file_name = QUrl(
                    str(data.data("text/uri-list"), encoding="utf-8").strip()
                ).toLocalFile()

                # The given URL was not a local file or the file does not exist
                if not file_name or not os.path.isfile(file_name):
                    return False
                return self.import_from_file(file_name)
            return False

    def mimeTypes(self) -> typing.List:
        return ["text/uri-list"]

    def mimeTypes(self) -> typing.List:
        return ["cutevariant/typed-json", "text/plain"]

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        return super().flags(index) | Qt.ItemIsDragEnabled | Qt.ItemIsDropEnabled


class WordSetWidget(PluginWidget):
    """Plugin to show handle word sets from user and gather matching variants
    as a new selection.
    """

    ENABLE = True

    def __init__(self, parent=None):
        super().__init__(parent)
        self.conn = None
        self.model = WordsetCollectionModel(parent=self)
        self.setWindowIcon(FIcon(0xF10E3))
        self.toolbar = QToolBar(self)
        self.view = QTableView(self)
        self.view.setSortingEnabled(True)
        self.view.setShowGrid(False)
        self.view.setAlternatingRowColors(False)
        self.view.setModel(self.model)
        self.view.setIconSize(QSize(16, 16))
        self.view.doubleClicked.connect(self.open_wordset)
        self.view.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.view.setSelectionBehavior(QAbstractItemView.SelectRows)

        self.view.setDragEnabled(True)
        self.view.setAcceptDrops(True)

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
        self.remove_action.setShortcut(QKeySequence.Delete)

        self.intersect_action = self.toolbar.addAction(
            FIcon(0xF0779),
            self.tr("Intersection of selected wordset"),
            lambda: self.on_apply_set_operation("intersect"),
        )
        self.union_action = self.toolbar.addAction(
            FIcon(0xF0778),
            self.tr("Union of selected wordset"),
            lambda: self.on_apply_set_operation("union"),
        )
        self.difference_action = self.toolbar.addAction(
            FIcon(0xF077B),
            self.tr("Difference of selected wordsets"),
            lambda: self.on_apply_set_operation("subtract"),
        )

        self.edit_action.setEnabled(False)
        self.remove_action.setEnabled(False)
        self.intersect_action.setEnabled(False)
        self.union_action.setEnabled(False)
        self.difference_action.setEnabled(False)

        v_layout = QVBoxLayout()
        v_layout.setContentsMargins(0, 0, 0, 0)
        v_layout.setSpacing(0)

        v_layout.addWidget(self.toolbar)
        v_layout.addWidget(self.view)

        self.setLayout(v_layout)

        # Item selected in view
        self.view.selectionModel().selectionChanged.connect(self.on_item_selected)

        self.addActions(self.toolbar.actions())
        self.setContextMenuPolicy(Qt.ActionsContextMenu)

    def update_action_availabilty(self):
        # Get list of all selected model item indexes
        enable = bool(self.view.selectionModel().selectedIndexes())

        self.edit_action.setEnabled(enable)
        self.remove_action.setEnabled(enable)
        self.intersect_action.setEnabled(enable)
        self.union_action.setEnabled(enable)
        self.difference_action.setEnabled(enable)

    def on_item_selected(self, *args):
        """Enable actions when an item is selected"""
        self.update_action_availabilty()

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
        fd, filename = tempfile.mkstemp()
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

        os.close(fd)
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

            if wordset_name in self.model.wordset_names():
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
        if not self.view.selectionModel().selectedIndexes():
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
        for selected_index in self.view.selectionModel().selectedRows(0):
            result = drop_cmd(
                self.conn, "wordsets", selected_index.data(Qt.DisplayRole)
            )

            if not result["success"]:
                LOGGER.error(result)
                QMessageBox.critical(
                    self,
                    self.tr("Error while deleting set"),
                    self.tr("Error while deleting set '%s'")
                    % selected_index.data(Qt.DisplayRole),
                )

        self.populate()

    def open_wordset(self):
        """Display a window to allow to edit the selected word set

        The previous set is dropped and the new is then imported in database.
        """
        wordset_index = (
            self.view.selectionModel().selectedRows(0)[0]
            if self.view.selectionModel().selectedRows(0)
            else None
        )
        if not wordset_index:
            return
        wordset_name = wordset_index.data(Qt.DisplayRole)
        dialog = WordListDialog()

        # populate dialog
        dialog.model.setStringList(list(get_words_in_set(self.conn, wordset_name)))

        if dialog.exec_() == QDialog.Accepted:
            drop_cmd(self.conn, "wordsets", wordset_name)
            # Import new
            self.import_wordset(dialog.model.stringList(), wordset_name)
            self.populate()

    def on_open_project(self, conn):
        """override"""
        self.conn = conn
        self.model.conn = conn
        self.on_refresh()

    def on_refresh(self):
        """override"""
        if self.conn:
            self.populate()
        else:
            self.model.clear()

    def populate(self):
        """Actualize the list of word sets"""
        self.model.load()
        self.view.horizontalHeader().setStretchLastSection(False)
        self.view.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.view.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeToContents
        )
        self.update_action_availabilty()

    def on_apply_set_operation(self, operation="intersect"):
        """Creates a new wordset from the union of selected wordsets.
        The resulting wordset will contain all elements from all selected wordsets, without double.
        """
        operations = {
            "intersect": (intersect_wordset, self.tr("Intersect")),
            "union": (union_wordset, self.tr("Union")),
            "subtract": (subtract_wordset, self.tr("Subtract")),
        }
        selected_wordsets = [
            index.data(Qt.DisplayRole)
            for index in self.view.selectionModel().selectedRows(0)
        ]
        if not selected_wordsets:
            return
        else:
            wordset_name = None
            while not wordset_name:
                wordset_name, _ = QInputDialog.getText(
                    self,
                    self.tr(f"New set ({operations[operation][1]})"),
                    self.tr("Name of the new set"),
                    QLineEdit.Normal,
                    self.tr(f"Wordset n°{self.model.rowCount()+1}"),
                )
                # self.tr(f"from {', '.join(selected_wordsets)}")
                if not wordset_name:
                    return

                if wordset_name in self.model.wordset_names():
                    # Name already used
                    QMessageBox.critical(
                        self,
                        self.tr("Error while creating set"),
                        self.tr("Error while creating set '%s'; Name is already used")
                        % wordset_name,
                    )
                    wordset_name = None
            operator_fn = operations.get(operation, intersect_wordset)[0]
            operator_fn(self.conn, wordset_name, selected_wordsets)
            self.populate()

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        """[summary]

        Args:
            event (QContextMenuEvent): context menu event (with click position and so on)
        """
        pass


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
