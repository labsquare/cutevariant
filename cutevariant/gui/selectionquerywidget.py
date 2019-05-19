"""Plugin to view/edit/remove/do set operations on selections in the database
from the GUI.

SelectionQueryWidget class is seen by the user and uses SelectionQueryModel class
as a model that handles records from the database.
"""
# Qt imports
from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *

# Custom imports
from .plugin import QueryPluginWidget
from cutevariant.core import Query
from cutevariant.core import sql
from cutevariant.gui.ficon import FIcon
from cutevariant.commons import logger, DEFAULT_SELECTION_NAME


LOGGER = logger()

# =================== SELECTION MODEL ===========================
class SelectionQueryModel(QAbstractTableModel):
    """Model to store all selections from SQLite `selections` table.

    Usage:

        model = SelectionQueryModel()
        model.query = query
        model.load()

    """

    def __init__(self):
        super().__init__()
        self._query = None
        self.records = []

    def rowCount(self, parent=QModelIndex()):
        """Overrided from QAbstractTableModel"""
        return len(self.records)

    def columnCount(self, parent=QModelIndex()):
        """Overrided from QAbstractTableModel"""
        return 2  #  value and count

    def data(self, index: QModelIndex(), role=Qt.DisplayRole):
        """Return the data stored under the given role for the item referred
        to by the index (row, col)

        Overrided from QAbstractTableModel

        :param index:
        :param role:
        :type index:
        :type role:
        :return: None if no valid index
        :rtype:
        """

        if not index.isValid():
            return None

        if role == Qt.DisplayRole:
            if index.column() == 0:
                return self.records[index.row()]["name"]

            if index.column() == 1:
                return self.records[index.row()]["count"]

        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        """Return the data for the given role and section in the header with
        the specified orientation

        Overrided from QAbstractTableModel
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

    def record(self, index: QModelIndex()):
        """Return Selection records by index"""
        if not index.isValid():
            return None
        return self.records[index.row()]

    def find_record(self, name: str):
        """Find a record by name
        @see: view.selectionModel()
        :return: Tuple of index in the model, and the record itself.
        :rtype: <tuple <int>, <str>>
        """
        for idx, record in enumerate(self.records):
            if record["name"] == name:
                return idx, record
        return None

    def remove_record(self, index: QModelIndex()):
        """Delete the selection with the given id in the database

        :return: True if the deletion has been made, False otherwise.
        :rtype: <boolean>
        """
        # Get selected record
        record = self.record(index)
        # Delete in database
        if sql.delete_selection(self.query.conn, record["id"]):
            # Delete in model; triggers currentRowChanged signal
            self.beginRemoveRows(QModelIndex(), index.row(), index.row())
            # Delete in records
            self.records.pop(index.row())
            self.endRemoveRows()
            return True
        return False

    def edit_record(self, index, record: dict):
        """Edit the given selection in the database and emit `dataChanged` signal"""
        if sql.edit_selection(self.query.conn, record):
            self.dataChanged.emit(index, index)

    @property
    def query(self):
        return self._query

    @query.setter
    def query(self, query: Query):
        self._query = query

    def load(self):
        """Load all selections into the model"""
        self.beginResetModel()
        # Add all selections from the database
        # Dictionnary of all attributes of the table.
        #    :Example: {"name": ..., "count": ..., "query": ...}
        self.records = list(sql.get_selections(self._query.conn))
        self.endResetModel()

    def save_current_query(self, name):
        """Save current query as a new selection and reload the model"""
        # TODO: just get the id of the created selection and add a new record
        # instead of reloading all the model...
        if self.query.create_selection(name):
            self.load()


# =================== SELECTION VIEW ===========================


class SelectionQueryWidget(QueryPluginWidget):
    """Widget displaying the list of avaible selections.
    User can select one of them to update Query::selection
    """

    def __init__(self):
        super().__init__()

        self.setWindowTitle(self.tr("Selections"))

        self.model = SelectionQueryModel()
        self.view = QTableView()
        self.view.setModel(self.model)
        self.view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.view.setSelectionMode(QAbstractItemView.SingleSelection)
        self.view.horizontalHeader().hide()
        # self.view.horizontalHeader().setStretchLastSection(True)

        self.view.verticalHeader().show()
        self.view.verticalHeader().setDefaultSectionSize(26)
        self.view.setShowGrid(False)
        self.view.setAlternatingRowColors(True)

        layout = QVBoxLayout()
        layout.addWidget(self.view)
        layout.setContentsMargins(0, 0, 0, 0)

        self.setLayout(layout)

        # call on_current_row_changed when item selection changed
        self.view.selectionModel().currentRowChanged.connect(
            self.on_current_row_changed
        )

    def menu_setup(self, locked_selection=False):
        """Setup popup menu
        :key locked_selection: Allow to mask edit/remove actions (default False)
        :type locked_selection: <boolean>
        """
        menu = QMenu()

        if not locked_selection:
            menu.addAction(FIcon(0xF8FF), self.tr("Edit"), self.edit_selection)

        # Set operations on selections: create mapping and actions
        set_icons_ids = (0xF55D, 0xF55B, 0xF564)
        set_texts = (self.tr("Intersect"), self.tr("Difference"), self.tr("Union"))
        set_internal_ids = ("intersect", "difference", "union")
        # Map the operations with an internal id not visible for the user
        # This id is used by _create_set_operation_menu and _make_set_operation
        # Keys: user text; values: internal ids
        self.set_operations_mapping = dict(zip(set_texts, set_internal_ids))

        # Create actions
        [
            menu.addMenu(self._create_set_operation_menu(FIcon(icon_id), text))
            for icon_id, text in zip(set_icons_ids, set_texts)
        ]

        if not locked_selection:
            menu.addSeparator()
            menu.addAction(FIcon(0xF413), self.tr("Remove"), self.remove_selection)
        return menu

    def load(self):
        """Load selection model and update the view"""
        # Block signals during the insertions
        self.view.selectionModel().blockSignals(True)
        self.model.load()
        self.view.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.view.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeToContents
        )

        # Select record according to query.selection
        row, _ = self.model.find_record(self.query.selection)
        if row is not None:
            self.view.selectRow(row)

        self.view.selectionModel().blockSignals(False)

    def on_change_query(self):
        """Overrided from AbstractQueryWidget"""
        self.load()

    def on_init_query(self):
        """Overrided from AbstractQueryWidget"""
        self.model.query = self.query

    def on_current_row_changed(self, index):
        """Update query when a selection item is clicked

        .. note:: Slot called when item selection is changed.
        """
        # We don't really care of the query that created the selection
        # The joins are based on the name of the table
        self.query.selection = self.model.record(index)["name"]
        self.query_changed.emit()

    def save_current_query(self):
        """Open a dialog box to save the current query into a selection"""
        name, success = QInputDialog.getText(
            self,
            self.tr("Type a name for selection"),
            self.tr("Selection name:"),
            QLineEdit.Normal,
        )
        if not success:
            return

        if name == DEFAULT_SELECTION_NAME:
            LOGGER.error(
                "SelectionQueryWidget:save_current_query:: '%s' is a reserved name for a selection.",
                name,
            )
            self.message.emit(
                self.tr("'%s' is a reserved name for a selection!") % name
            )
        elif name in {record["name"] for record in self.model.records}:
            LOGGER.error(
                "SelectionQueryWidget:save_current_query:: '%s' is a already used.",
                name,
            )
            self.message.emit(self.tr("'%s' is a already used for a selection!") % name)
        else:
            self.model.save_current_query(name)

    def contextMenuEvent(self, event: QContextMenuEvent):
        """Overrided: Show popup menu at the cursor position"""
        if not self.model.records:
            return
        # Detect locked selection to mask edit/remove actions
        locked_selection = False
        current_index = self.view.selectionModel().currentIndex()
        record = self.model.record(current_index)
        if record["name"] == DEFAULT_SELECTION_NAME:
            locked_selection = True
        # Show the menu
        menu = self.menu_setup(locked_selection)
        menu.exec_(event.globalPos())

    def _create_set_operation_menu(self, icon, menu_name):
        """Dynamically add submenu with the given name to popup menu"""
        menu = QMenu(menu_name)
        menu.setIcon(icon)

        # Get all the names of selections except the current one
        current_selection_name = self.model.record(self.view.currentIndex())["name"]
        records_names = set(record["name"] for record in self.model.records)
        records_names.remove(current_selection_name)

        # Create an action in the menu for all the remaining elements
        for record_name in records_names:
            action = menu.addAction(record_name)
            # This hidden data is used by _make_set_operation() to detect
            # which operation to do
            action.setData(self.set_operations_mapping[menu_name])
            action.triggered.connect(self._make_set_operation)

        return menu

    def _make_set_operation(self):
        """Do set operation

        .. note:: Called when a "set" submenu of the popup menu is triggered.
        """
        action = self.sender()

        # Get menu id to know which set operation to do
        set_internal_id = action.data()

        # Init class attribute
        sql.Selection.conn = self.query.conn

        # Get the records and extract their database id to build 2 Selections objects
        record_1 = self.model.record(self.view.selectionModel().currentIndex())
        _, record_2 = self.model.find_record(action.text())
        # TODO: handle modes for creation of selections
        selection_1 = sql.Selection.from_selection_id(record_1["id"])
        selection_2 = sql.Selection.from_selection_id(record_2["id"])

        new_selection_name, success = QInputDialog.getText(
            self, self.tr("Type a name for selection"), self.tr("Selection name:")
        )
        if not success:
            return

        # Do set operation and create new selection
        if set_internal_id == "union":
            selection_3 = selection_1 + selection_2
        if set_internal_id == "difference":
            selection_3 = selection_1 - selection_2
        if set_internal_id == "intersect":
            selection_3 = selection_1 & selection_2

        LOGGER.debug(
            "Query:_make_set_operation:: New selection query: %s", selection_3.sql_query
        )

        if not selection_3.save(new_selection_name):
            self.message.emit(self.tr("Fail to create the selection!"))
            return
        # Reload the model
        self.model.load()

    def remove_selection(self):
        """Remove a selection from the database"""
        msg = QMessageBox()
        msg.setText(self.tr("Are you sure you want to remove this selection?"))
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)

        if msg.exec_() == QMessageBox.Yes:
            for index in self.view.selectionModel().selectedRows():
                self.model.remove_record(index)

    def edit_selection(self):
        """Update a selection in the database
        .. note:: We do not reload all the UI for this
        """
        current_index = self.view.selectionModel().currentIndex()
        new_name = QInputDialog.getText(
            self, self.tr("Type a new name"), self.tr("Selection name:")
        )
        if new_name[1] and current_index:
            old_record = self.model.record(current_index)
            old_record["name"] = new_name[0]
            self.model.edit_record(current_index, old_record)
