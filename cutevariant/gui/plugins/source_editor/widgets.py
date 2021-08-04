"""Plugin to view/edit/remove/do set operations on selections in the database
from the GUI.
SourceEditorWidget class is seen by the user and uses selectionModel class
as a model that handles records from the database.
"""
from logging import currentframe
from cutevariant.gui.widgets.searchable_table_widget import LoadingTableView
import typing

# Qt imports
from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *

# Custom imports
from cutevariant.core import sql, command
from cutevariant.core.sql import (
    create_selection,
    intersect_variants,
    union_variants,
    subtract_variants,
)
from cutevariant.core.reader import BedReader
from cutevariant.gui import plugin, FIcon
from cutevariant.gui.widgets import SearchableTableWidget
from cutevariant.commons import DEFAULT_SELECTION_NAME


from cutevariant import LOGGER

# =================== SELECTION MODEL ===========================
class SourceModel(QAbstractTableModel):
    """Model to store all sources from SQLite `selections` table.

    Note:
        A source is a variant selection stored into `selection` tables.

    Usage:
        model = selectionModel()
        model.conn = conn
        model.load()
    """

    def __init__(self, conn=None):
        super().__init__()
        self.conn = conn
        self.records = []

        self._current_source = "variants"

    @property
    def current_source(self) -> str:
        return self._current_source

    @current_source.setter
    def current_source(self, value: str):
        old_index = self.find_record(self._current_source)
        self._current_source = value
        new_index = self.find_record(self._current_source)
        if old_index != new_index:
            self.dataChanged.emit(old_index, old_index.siblingAtColumn(1))
            self.dataChanged.emit(new_index, new_index.siblingAtColumn(1))

    def rowCount(self, parent=QModelIndex()) -> int:
        """Overrided from QAbstractTableModel"""
        return len(self.records)

    def columnCount(self, parent=QModelIndex()) -> int:
        """Overrided from QAbstractTableModel"""
        return 2  # value and count

    def data(self, index: QModelIndex, role=Qt.DisplayRole) -> typing.Any:
        """Override from QAbstractTableModel

        Args:
            index (QModelIndex)
            role (Qt.ItemDataRole) Defaults to Qt.DisplayRole.

        Returns:
            Any
        """

        if not index.isValid() or index.row() < 0 or index.row() >= self.rowCount():
            return None

        table_name = self.records[index.row()]["name"]

        if role == Qt.DisplayRole:
            if index.column() == 0:
                return self.records[index.row()]["name"]

            if index.column() == 1:
                return self.records[index.row()]["count"]

        if role == Qt.ToolTipRole:
            vql_query = self.records[index.row()]["query"]
            if vql_query:
                return vql_query.replace("SELECT id", "")
            else:
                return "All variants"

        if role == Qt.DecorationRole:
            if index.column() == 0:
                if table_name == DEFAULT_SELECTION_NAME:
                    return QIcon(FIcon(0xF13C6))
                else:
                    return QIcon(FIcon(0xF04EB))

        if role == Qt.FontRole:
            font = QFont()
            if table_name == self.current_source:
                font.setBold(True)
            return font

        if role == Qt.UserRole:
            return self.records[index.row()]

        if role == Qt.UserRole:
            return self.records[index.row()]

        return None

    def headerData(
        self, section: int, orientation: Qt.Orientation, role=Qt.DisplayRole
    ) -> str:
        """Override from QAbstractTableModel

        Args:
            section (int): Header index
            orientation (Qt.Orientation): Header orientation
            role (Qt.ItemRole, optional) Defaults to Qt.DisplayRole.

        Returns:
            str: [description]
        """
        if not self.records:
            return

        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            if section == 0:
                return "selection"
            if section == 1:
                return "count"

        if orientation == Qt.Vertical and role == Qt.DisplayRole and section > 0:
            return self.records[section].get(
                "id", None
            )  # For debug purpose . displayed in vertical header

    def record(self, index: QModelIndex()) -> dict:
        """Return source item

        See ```cutevariant.sql.get_selection```

        Args:
            index (QModelIndex)

        Returns:
            dict
        """
        if not index.isValid():
            return None
        return self.records[index.row()]

    def find_record(self, name: str) -> QModelIndex:
        """Find a record by name

        Returns:
            QModelIndex
        """
        for idx, record in enumerate(self.records):
            if record["name"] == name:
                return self.index(idx, 0, QModelIndex())
        return QModelIndex()

    def remove_record(self, index: QModelIndex()) -> bool:
        """Delete the selection with the given id in the database
        Returns:
            bool: Return True if the deletion has been made, False otherwise.
        """
        # Get selected record
        return self.remove_records([index])

    def remove_records(self, indexes: typing.List[QModelIndex]) -> bool:
        """Delete the selection with the given id in the database
        Returns:
            bool: Return True if the deletion has been made, False otherwise.
        """
        # Get selected record
        rows = sorted([index.row() for index in indexes], reverse=True)
        for row in rows:
            record = self.record(self.index(row, 0))

            if sql.delete_selection(self.conn, record["id"]):
                self.beginRemoveRows(QModelIndex(), row, row)
                # Delete in model; triggers currentRowChanged signal
                #  Magic... the record disapear ...  ??
                # No, it didn't. But below line does
                del self.records[row]
                self.endRemoveRows()
            else:
                return False
        return True

    def edit_record(self, index: QModelIndex, record: dict):
        """Edit the given selection in the database and emit `dataChanged` signal"""
        if sql.edit_selection(self.conn, record):
            self.dataChanged.emit(index, index)

    def load(self):
        """Load all selections into the model"""

        if self.conn is None:
            return
        self.beginResetModel()
        # Add all selections from the database
        # Dictionnary of all attributes of the table.
        #    :Example: {"name": ..., "count": ..., "query": ...}
        self.records = list(sql.get_selections(self.conn))
        self.endResetModel()

    def get_source_names(self):
        return [rec["name"] for rec in self.records]


# =================== SELECTION VIEW ===========================


class SourceEditorWidget(plugin.PluginWidget):
    """Widget displaying the list of avaible selections.
    User can select one of them to update Query::selection
    """

    ENABLE = True
    REFRESH_STATE_DATA = {"source"}

    def __init__(self, parent=None, conn=None):
        """
        Args:
            parent (QWidget)
            conn (sqlite3.connexion): sqlite3 connexion
        """
        super().__init__(parent)

        self.setWindowIcon(FIcon(0xF10E4))
        # conn is always None here but initialized in on_open_project()
        self.model = SourceModel(conn)
        self.view = LoadingTableView()
        self.view.setModel(self.model)
        self.view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.view.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.view.horizontalHeader().setStretchLastSection(False)
        self.view.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.view.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeToContents
        )
        self.view.setSortingEnabled(True)
        self.view.setShowGrid(False)
        self.view.setAlternatingRowColors(False)
        self.view.setIconSize(QSize(22, 22))

        self.toolbar = QToolBar()
        self.toolbar.setIconSize(QSize(16, 16))
        self.toolbar.setToolButtonStyle(Qt.ToolButtonIconOnly)

        self.view.verticalHeader().hide()
        # self.view.verticalHeader().setDefaultSectionSize(26)

        layout = QVBoxLayout()
        layout.addWidget(self.toolbar)
        layout.addWidget(self.view)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.setLayout(layout)

        # Used to block signals during the insertions (if set to True)
        self.is_loading = False

        # call on_current_row_changed when item selection changed
        self.view.doubleClicked.connect(self.on_double_click)

        self.create_selection_action = self.toolbar.addAction(
            FIcon(0xF0F87),
            self.tr("New source..."),
            self.create_selection_from_current,
        )
        self.create_selection_from_bed_action = self.toolbar.addAction(
            FIcon(0xF0965),
            self.tr("Intersect with BED file"),
            self.create_selection_from_bed,
        )
        self.create_selection_from_bed_action.setToolTip(
            "Create new source from intersection with BED file"
        )

        # Add action to rename source
        self.edit_action = self.toolbar.addAction(
            FIcon(0xF04F0), self.tr("Rename source"), self.edit_selection
        )
        self.edit_action.setEnabled(False)

        # Add action to delete source
        self.del_action = self.toolbar.addAction(
            FIcon(0xF0A76), self.tr("Delete source"), self.remove_selection
        )
        self.del_action.setEnabled(False)

        # Add all three set operations
        self.intersect_action = self.toolbar.addAction(
            FIcon(0xF0779),
            self.tr("Intersection of selected sources"),
            lambda: self.on_apply_set_operation("intersect"),
        )
        self.union_action = self.toolbar.addAction(
            FIcon(0xF0778),
            self.tr("Union of selected sources"),
            lambda: self.on_apply_set_operation("union"),
        )
        self.difference_action = self.toolbar.addAction(
            FIcon(0xF077B),
            self.tr("Difference between selected sources (First - Last)"),
            lambda: self.on_apply_set_operation("subtract"),
        )

        self.intersect_action.setEnabled(False)
        self.union_action.setEnabled(False)
        self.difference_action.setEnabled(False)

        # Add all actions from toolbar to this widget's actions (except for the drop down 'add' action that has no text)
        self.addActions(self.toolbar.actions())

        # When right cliking, this will show the same actions as the toolbar
        self.setContextMenuPolicy(Qt.ActionsContextMenu)

        self.view.selectionModel().selectionChanged.connect(self.on_selection_changed)

        # self.toolbar.addAction(FIcon(0xF0453), self.tr("Reload"), self.load)

    @Slot(QModelIndex)
    def on_double_click(self, current: QModelIndex):
        source = current.data(Qt.DisplayRole)
        if source:
            self.model.current_source = source
            self.mainwindow.set_state_data("source", source)
            self.mainwindow.refresh_plugins(sender=self)

    def create_selection_from_current(self):
        name = self.ask_and_check_selection_name()

        if name:

            executed_query_data = self.mainwindow.get_state_data("executed_query_data")

            result = command.create_cmd(
                self.conn,
                name,
                source=self.mainwindow.get_state_data("source"),
                filters=self.mainwindow.get_state_data("filters"),
                count=executed_query_data.get("count", 0),
            )

            if result:
                self.on_refresh()

    def create_selection_from_bed(self):
        """Create a selection from a selected bed file

        Note:
            This method is called by a toolbar QAction

        """
        # Reload last directory used
        app_settings = QSettings()
        last_directory = app_settings.value("last_directory", QDir.homePath())

        filepath, _ = QFileDialog.getOpenFileName(
            self,
            self.tr("Intersect variants with a bed file"),
            last_directory,
            self.tr("BED - Browser Extensible Data (*.bed)"),
        )
        if not filepath:
            return

        selection_name = self.ask_and_check_selection_name(placeholder="my_panel")
        if not selection_name:
            return

        # Open bed intervals & create selection
        intervals = BedReader(filepath)
        sql.create_selection_from_bed(
            self.model.conn, DEFAULT_SELECTION_NAME, selection_name, intervals
        )
        # Refresh UI
        self.model.load()

    def on_open_project(self, conn):
        """override from PluginWidget"""
        self.model.conn = conn
        self.conn = conn
        self.on_refresh()

    def on_refresh(self):
        """override from PluginWidget"""
        # self.view.selectionModel().blockSignals(True)
        self.model.load()
        self.source = self.mainwindow.get_state_data("source")
        self.model.current_source = self.source
        # model_index = self.model.find_record(self.source)
        # self.view.setCurrentIndex(model_index)
        # self.view.selectionModel().blockSignals(False)

    def on_selection_changed(
        self,
        selected,
        deselected,
    ):
        """Called when the source selection has changed. The change is already applied when this callback is triggered.
        For this widget, it allows us to check whether the number of selected sources is exactly two, so we can enable/disable the set operations
        """
        selected_sources = [
            index.data(Qt.DisplayRole)
            for index in self.view.selectionModel().selectedRows(0)
        ]

        if not selected_sources:
            # No source selected whatsoever, cannot apply any operation. Disable every action (except create selection from source)
            self.intersect_action.setEnabled(False)
            self.difference_action.setEnabled(False)
            self.union_action.setEnabled(False)

            self.edit_action.setEnabled(False)
            self.del_action.setEnabled(False)
            return

        # Set operations are enable iff the number of selected sources is exactly two
        is_selection_count_valid = len(selected_sources) == 2
        self.intersect_action.setEnabled(is_selection_count_valid)
        self.difference_action.setEnabled(is_selection_count_valid)
        self.union_action.setEnabled(is_selection_count_valid)

        current = self.view.selectionModel().currentIndex()

        self.create_selection_from_bed_action.setEnabled(
            current.data(Qt.DisplayRole) == DEFAULT_SELECTION_NAME
        )

        if any(source == DEFAULT_SELECTION_NAME for source in selected_sources):
            self.edit_action.setEnabled(False)
            self.del_action.setEnabled(False)
        else:
            self.edit_action.setEnabled(True)
            self.del_action.setEnabled(True)

    def load(self):
        """Load selection model and update the view"""
        # Block signals during the insertions
        self.is_loading = True
        self.model.load()

        # Select record according to query.selection
        current_index = 0
        if self.source:
            current_index = self.model.find_record(self.source)
        self.view.setCurrentIndex(current_index)

        self.is_loading = False

    def ask_and_check_selection_name(self, placeholder: str = ""):
        """Get from the user a selection name validated or None

        TODO : create a sql.selection_exists(name) to check if selection already exists
        """
        name, success = QInputDialog.getText(
            self,
            self.tr("Type a name for selection"),
            self.tr("Selection name:"),
            QLineEdit.Normal,
            placeholder,
        )
        if not success:
            return

        if name == DEFAULT_SELECTION_NAME:
            LOGGER.error(
                "SourceEditorWidget:save_current_query:: '%s' is a reserved name for a selection.",
                name,
            )
            self.mainwindow.status_bar.showMessage(
                self.tr("'%s' is a reserved name for a selection!") % name
            )
            QMessageBox.critical(
                self,
                self.tr("Error while creating the selection"),
                self.tr("'%s' is a reserved name for a selection!") % name,
            )
        elif name in self.model.get_source_names():
            LOGGER.error(
                "SourceEditorWidget:save_current_query:: '%s' is already used!", name
            )
            self.mainwindow.status_bar.showMessage(
                self.tr("'%s' is already used for a selection!") % name
            )
            QMessageBox.critical(
                self,
                self.tr("Error while creating the selection"),
                self.tr("'%s' is already used for a selection!") % name,
            )
        else:
            return name

    def remove_selection(self):
        """Remove a selection from the database"""

        if not self.view.selectionModel().selectedRows(0):
            QMessageBox.information(
                self, self.tr("Info"), self.tr("No source to remove!")
            )
            return

        # This should not even be called, since remove/edit actions are supposed to be disabled by the widget
        if any(
            self.model.record(row) == DEFAULT_SELECTION_NAME
            for row in self.view.selectionModel().selectedRows(0)
        ):
            QMessageBox.warning(
                self,
                self.tr("Remove source"),
                self.tr("Removing the root table is forbidden"),
            )
            return

        msg = QMessageBox(icon=QMessageBox.Warning)
        msg.setText(self.tr("Are you sure you want to remove this selection?"))
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)

        if msg.exec_() == QMessageBox.Yes:
            self.model.remove_records(self.view.selectionModel().selectedRows(0))

            self.mainwindow.set_state_data("source", DEFAULT_SELECTION_NAME)
            self.mainwindow.refresh_plugins(sender=None)

    def edit_selection(self):
        """Update a selection in the database
        .. note:: We do not reload all the UI for this
        """
        current_index = self.view.selectionModel().currentIndex()
        if not current_index.isValid():
            QMessageBox.information(
                self, self.tr("Info"), self.tr("No source to edit!")
            )
        old_record = self.model.record(current_index)

        selection_name = self.ask_and_check_selection_name(
            placeholder=old_record["name"]
        )
        if current_index and selection_name:
            old_record["name"] = selection_name
            self.model.edit_record(current_index, old_record)
            self.mainwindow.set_state_data("source", selection_name)
            self.mainwindow.refresh_plugins(sender=None)

    def on_apply_set_operation(self, operation="intersect"):
        """Creates a new wordset from the union of selected wordsets.
        The resulting wordset will contain all elements from all selected wordsets, without double.
        """
        operators = {"intersect": "AND", "union": "OR", "subtract": "MINUS"}
        operations = {
            "intersect": (
                lambda name, first, last: command.set_cmd(
                    self.conn, name, first, last, "&"
                ),
                self.tr("intersection"),
            ),
            "union": (
                lambda name, first, last: command.set_cmd(
                    self.conn, name, first, last, "|"
                ),
                self.tr("union"),
            ),
            "subtract": (
                lambda name, first, last: command.set_cmd(
                    self.conn, name, first, last, "-"
                ),
                self.tr("difference"),
            ),
        }
        selected_sources = [
            index.data(Qt.DisplayRole)
            for index in self.view.selectionModel().selectedRows(0)
        ]
        if not selected_sources:
            return
        else:
            # Kind reminder to the user of what the operation will be about
            if (
                QMessageBox.question(
                    self,
                    self.tr(f"Set operation on sources"),
                    self.tr(
                        'This will perform "{first}" {operator} "{last}". Continue?'
                    ).format(
                        first=selected_sources[0],
                        operator=operators[operation],
                        last=selected_sources[1],
                    ),
                )
                != QMessageBox.Yes
            ):
                return
            selection_name = None
            while not selection_name:
                selection_name, _ = QInputDialog.getText(
                    self,
                    self.tr(f"New source from {operations[operation][1]}"),
                    self.tr("Name of the new source"),
                    QLineEdit.Normal,
                    self.tr(f"Source n°{self.model.rowCount()+1}"),
                )
                if not selection_name:
                    return

                if selection_name in self.model.get_source_names():
                    # Name already used
                    QMessageBox.critical(
                        self,
                        self.tr("Error while creating set"),
                        self.tr("Error while creating set '%s'; Name is already used")
                        % selection_name,
                    )
                    selection_name = None
            if operation not in operations:
                return
            operator_fn = operations[operation][0]
            if operator_fn(selection_name, selected_sources[0], selected_sources[1]):
                QMessageBox.information(
                    self,
                    self.tr("Success!"),
                    self.tr(f"Successfully created source {selection_name} !"),
                )
                self.mainwindow.set_state_data("source", selection_name)
                self.mainwindow.refresh_plugins(sender=None)
            else:
                QMessageBox.warning(
                    self,
                    self.tr("Warning!"),
                    self.tr(
                        "No source created! Usually, this is because the resulting selection is empty.\nDid you invert the order of difference operator?"
                    ),
                )


if __name__ == "__main__":

    import sqlite3
    import sys
    from PySide2.QtWidgets import QApplication

    app = QApplication(sys.argv)

    view = SourceEditorWidget(conn=sqlite3.connect("examples/test.snpeff.vcf.db"))
    view.show()

    app.exec_()
