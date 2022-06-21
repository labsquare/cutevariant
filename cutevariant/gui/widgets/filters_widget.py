import sqlite3
from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

from functools import lru_cache
import sys
import json
import os
import pickle
import typing
import uuid
from typing import Any, Iterable

from cutevariant.gui import mainwindow, style, plugin, FIcon
from cutevariant import constants as cst
from cutevariant.core import sql, get_sql_connection
from cutevariant.core.vql import parse_one_vql
from cutevariant.core.querybuilder import (
    build_vql_query,
    fields_to_vql,
)
from cutevariant.core.querybuilder import PY_TO_VQL_OPERATORS


OPERATOR_VQL_TO_NAME = {
    "$eq": "Equal to",
    "$gt": "Strictly greater than",
    "$gte": "Greater than ",
    "$lt": "Strictly less than",
    "$lte": "Less than",
    "$in": "In",
    "$nin": "Not in",
    "$ne": "Not equal to",
    "$regex": "Contains",
    "$nregex": "Does not contain",
    "$and": "And",
    "$or": "Or",
    "$has": "Has",
    "$nhas": "Has not",
}


DEFAULT_VALUES = {"str": "", "int": 0, "float": 0.0, "list": [], "bool": True}

NULL_REPR = "@NULL"

COLUMN_FIELD = 0
COLUMN_LOGIC = 0
COLUMN_OPERATOR = 1
COLUMN_VALUE = 2
COLUMN_CHECKBOX = 3
COLUMN_REMOVE = 4


@lru_cache()
def get_field_unique_values_cached(
    conn: sqlite3.Connection, field_name: str, like: str, limit: int
) -> list:
    """Used for autocompletion of the value field
    Return cached values of a specific field

    """
    return sql.get_field_unique_values(conn, field_name, like, limit)


@lru_cache()
def prepare_fields(conn) -> dict:
    """Used for autcompletion of the combobox field
    Prepares a  cached list of columns on which filters can be applied

    It returns dict[field_name] = field_type

    """
    results = {}
    samples = [sample["name"] for sample in sql.get_samples(conn)] + ["$any", "$all"]

    for field in sql.get_fields(conn):

        if field["category"] == "variants":
            name = field["name"]
            results[name] = field["type"]

        if field["category"] == "annotations":
            name = field["name"]
            results[f"ann.{name}"] = field["type"]

        if field["category"] == "samples":
            name = field["name"]
            for sample in samples:
                sample_field = f"samples.{sample}.{name}"
                results[sample_field] = field["type"]

    return results


class FieldsCompleter(QCompleter):
    """A custom completer to load fields values dynamically thanks to a SQL LIKE statement"""

    def __init__(self, conn=None, parent=None):
        super().__init__(parent)
        self.local_completion_prefix = ""
        self.source_model = QStringListModel()
        self.field_name = ""
        self.limit = 50
        self.conn = conn
        self.setCompletionMode(QCompleter.PopupCompletion)
        self.setModel(self.source_model)

    def setModel(self, model):
        """override"""
        self.source_model = model
        super().setModel(self.source_model)

    def updateModel(self):
        """update model from sql like"""
        if not self.conn or not self.field_name:
            return

        local_completion_prefix = self.local_completion_prefix

        like = f"{local_completion_prefix}%"
        values = get_field_unique_values_cached(self.conn, self.field_name, like, self.limit)
        self.source_model.setStringList(values)

    def splitPath(self, path: str):
        """override"""
        self.local_completion_prefix = path
        self.updateModel()
        return ""


class BaseFieldEditor(QFrame):
    """Base class for all editor widgets.

    Editor widgets are used in FilterDelegate to display different kind of
    editors according to field type.

    Inherit from this class if you want a custom field editor by overriding
    `set_value` and `get_value`.

    See Also:
         :meth:`FilterDelegate`
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        # style hack : Set background as same as selection in the view
        self.setAutoFillBackground(True)
        self.setBackgroundRole(QPalette.Highlight)
        self.vlayout = QHBoxLayout(self)
        self.vlayout.setContentsMargins(0, 0, 0, 0)
        self.vlayout.setSpacing(0)

    def set_button_icon(self, icon: QIcon):
        self.button.setIcon(icon)

    def set_value(self, value):
        raise NotImplementedError

    def get_value(self):
        raise NotImplementedError

    def reset(self):
        pass

    def on_press_tool_button(self):
        if hasattr(self, "widget"):
            self.widget.setDisabled(self.button.isChecked())

    def set_widget(self, widget):
        """Setup a layout with a widget

        Typically, it is used to add user input widget to the item
        (QSpinBox, QComboBox, etc.)

        Args:
            widget (QWidget)
        """
        self.widget = widget
        self.vlayout.insertWidget(0, self.widget)


class IntFieldEditor(BaseFieldEditor):
    """Editor for integer value

    Attributes:
        spin_box (QSpinBox)
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.line_edit = QLineEdit()
        self.validator = QIntValidator()
        self.line_edit.setValidator(self.validator)
        self.set_widget(self.line_edit)
        self.line_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        null_action = self.line_edit.addAction(FIcon(0xF07E2), QLineEdit.TrailingPosition)
        null_action.triggered.connect(lambda: self.line_edit.setText(NULL_REPR))
        null_action.setToolTip(self.tr("Set value as NULL"))

    def set_value(self, value: int):
        if value is None:
            self.line_edit.setText(NULL_REPR)
        else:
            self.line_edit.setText(str(value))

    def get_value(self) -> int:
        value = self.line_edit.text()
        if value == NULL_REPR:
            value = None
        else:
            value = int(self.line_edit.text())
        return value

    def set_range(self, min_, max_):
        """Limit editor with a range of value"""
        self.validator.setRange(min_, max_)


class DoubleFieldEditor(BaseFieldEditor):
    """Editor for floating point value

    Attributes:
        spin_box (QDoubleSpinBox)
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.line_edit = QLineEdit()
        self.validator = QDoubleValidator()
        self.line_edit.setValidator(self.validator)
        self.line_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        null_action = self.line_edit.addAction(FIcon(0xF07E2), QLineEdit.TrailingPosition)
        null_action.triggered.connect(lambda: self.line_edit.setText(NULL_REPR))

        self.set_widget(self.line_edit)

    def set_value(self, value: float):

        if value is None:
            self.line_edit.setText(NULL_REPR)
            return
        try:
            txt = QLocale().toString(value)
        except:
            txt = QLocale().toString(0.0)
        self.line_edit.setText(txt)

    def get_value(self) -> float:

        text = self.line_edit.text()

        if text == NULL_REPR:
            return None
        value = 0.0
        value, success = QLocale().toDouble(text)

        if not success:
            value = 0.0

        return value

    def set_range(self, min_, max_):
        self.validator.setRange(min_, max_)


class StrFieldEditor(BaseFieldEditor):
    """Editor for string value

    Attributes:
        edit (QLineEdit)
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.edit = QLineEdit()
        self.edit.setPlaceholderText("Enter a text ...")
        self.edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.set_widget(self.edit)
        null_action = self.edit.addAction(FIcon(0xF07E2), QLineEdit.TrailingPosition)
        null_action.triggered.connect(lambda: self.edit.setText(NULL_REPR))

    def set_value(self, value: str):
        """Set displayed value in the lineEdit of the editor"""
        if value is None:
            value = NULL_REPR
        self.edit.setText(str(value))

    def get_value(self) -> str:
        """Return string or float/int for numeric values"""
        value = self.edit.text()
        if value == NULL_REPR:
            value = None
        return value


class WordSetEditor(BaseFieldEditor):
    """Editor for Boolean value

    Attributes:
        box (QCheckBox)
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.w = QWidget()
        self.edit = QLineEdit()
        self.combo = QComboBox()
        self.stack = QStackedWidget()
        self.btn = QPushButton()
        self.btn.setFlat(True)
        self.btn.setToolTip(self.tr("Use wordset"))

        hlayout = QHBoxLayout()
        self.stack.addWidget(self.edit)
        self.stack.addWidget(self.combo)

        hlayout.addWidget(self.stack)
        hlayout.addWidget(self.btn)

        hlayout.setContentsMargins(0, 0, 0, 0)
        hlayout.setSpacing(0)
        self.w.setLayout(hlayout)
        self.set_mode("list")

        # DisplayRole, UserRole

        self.edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.btn.clicked.connect(self.switch_mode)

        self.set_widget(self.w)

    def switch_mode(self):
        next_mode = "list" if self.get_mode() == "wordset" else "wordset"
        self.set_mode(next_mode)

    def fill_wordsets(self, wordsets: list):
        self.combo.clear()
        self.combo.addItems(wordsets)

    def set_mode(self, mode="list"):
        """set mode with either 'list' or 'wordset'"""

        if mode == "list":
            self.stack.setCurrentIndex(0)
            self.btn.setIcon(FIcon(0xF0B13))
            self.btn.setToolTip(self.tr("Use wordset"))
        if mode == "wordset":
            self.stack.setCurrentIndex(1)
            self.btn.setIcon(FIcon(0xF0C2E))
            self.btn.setToolTip(self.tr("Use list"))

    def get_mode(self):
        return "list" if self.stack.currentIndex() == 0 else "wordset"

    def set_value(self, value: Any):

        # If value is a simple list of elements ...
        if isinstance(value, list):
            self.edit.setText(",".join(value))
            self.set_mode("list")

        # If it is a real wordset object
        if isinstance(value, dict):
            if "$wordset" in value:
                self.combo.setCurrentText(value["$wordset"])
                self.set_mode("wordset")

    def get_value(self) -> Any:

        # If has ",", it is a simple list list.
        if self.get_mode() == "list":  # ListMode
            return self.edit.text().split(",")
        else:
            return {"$wordset": self.combo.currentText()}


class BoolFieldEditor(BaseFieldEditor):
    """Editor for Boolean value

    Attributes:
        box (QCheckBox)
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.box = QComboBox()
        # DisplayRole, UserRole
        self.box.addItem("False", False)
        self.box.addItem("True", True)
        self.set_widget(self.box)
        self.box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def set_value(self, value: bool):
        self.box.setCurrentIndex(int(value))

    def get_value(self) -> bool:
        # Return UserRole
        return self.box.currentData()


class GenotypeFieldEditor(BaseFieldEditor):
    """Editor for Boolean value

    Attributes:
        box (QCheckBox)
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.box = QComboBox()
        # DisplayRole, UserRole
        self.box.addItem("0/1", 1)
        self.box.addItem("1/1", 2)
        self.box.addItem("0/0", 0)
        self.box.addItem("?/?", -1)

        self.set_widget(self.box)
        self.box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def set_value(self, value: int):
        self.box.setCurrentIndex(self.box.findData(value))

    def get_value(self) -> int:
        # Return UserRole
        return self.box.currentData()


class ComboFieldEditor(BaseFieldEditor):
    """Editor for Logic Value (less, greater, more than etc ...)

    Attributes:
        combo_box (QComboBox): Combobox to allow a suer to select operators.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.combo_box = QComboBox()
        self.set_widget(self.combo_box)
        self.combo_box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def set_value(self, value: str):
        self.combo_box.setCurrentText(value)

    def get_value(self) -> str:
        # Return UserRole
        return self.combo_box.currentText()

    def fill(self, items):
        self.combo_box.clear()
        self.combo_box.addItems(items)
        self.combo_box.completer().setFilterMode(Qt.MatchContains)
        self.combo_box.completer().setCompletionMode(QCompleter.PopupCompletion)

    def set_editable(self, active):
        self.combo_box.setEditable(True)


class OperatorFieldEditor(BaseFieldEditor):
    """Editor for Logic Value (less, greater, more than etc ...)

    Attributes:
        combo_box (QComboBox): Combobox to allow a suer to select operators.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.combo_box = QComboBox()
        self.set_widget(self.combo_box)
        self.combo_box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def set_value(self, value: str):
        self.combo_box.setCurrentText(value)

    def get_value(self) -> str:
        # Return UserRole
        return self.combo_box.currentData()

    def fill(self, operators=PY_TO_VQL_OPERATORS):
        """Init  with all supported operators"""
        self.combo_box.clear()
        for op in operators:
            if op not in ("$and", "$or"):
                self.combo_box.addItem(OPERATOR_VQL_TO_NAME[op], op)


class LogicFieldEditor(BaseFieldEditor):
    """Editor for logic field (And/Or)"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.box = QComboBox()

        # DisplayRole, UserRole
        self.box.addItem(OPERATOR_VQL_TO_NAME.get("$and"), "$and")
        self.box.addItem(OPERATOR_VQL_TO_NAME.get("$or"), "$or")

        self.box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.set_widget(self.box)

    def set_value(self, value: str):

        if value == "$or":
            self.box.setCurrentIndex(1)

        else:  # AND
            self.box.setCurrentIndex(0)

    def get_value(self) -> str:
        # Return UserRole
        return self.box.currentData()


class FieldFactory(QObject):
    """FieldFactory is a factory to build BaseEditor according sql Field data

    Attributes:
        conn (sqlite3.connection)

    TODO: used only in FieldDialog => not used anymore
    """

    def __init__(self, conn):
        super().__init__()
        self.conn = conn
        self.field_types_mapping = prepare_fields(self.conn)

    def create(self, field: str, operator=None, parent=None):
        """Get FieldWidget according to type key of the given sql_field"""

        field_type = self.field_types_mapping.get(field)

        if field.endswith(".gt"):
            w = GenotypeFieldEditor(parent)
            return w

        if operator in ("$in", "$nin"):
            w = WordSetEditor(parent)
            w.fill_wordsets([w["name"] for w in sql.get_wordsets(self.conn)])
            return w

        if field_type == "int":
            w = IntFieldEditor(parent)
            # w.set_range(*sql.get_field_range(self.conn, sql_field, sample))
            return w

        if field_type == "float":
            w = DoubleFieldEditor(parent)
            # w.set_range(*sql.get_field_range(self.conn, sql_field, sample))
            return w

        if field_type == "str":
            w = StrFieldEditor(parent)
            w.cc = FieldsCompleter(conn=self.conn, parent=parent)
            w.cc.field_name = field
            w.edit.setCompleter(w.cc)

            return w

        if field_type == "bool":
            return BoolFieldEditor(parent)

        LOGGER.warning("field is unknown")
        return StrFieldEditor(parent)


class FilterItem:
    """FilterItem is a recursive class which represent item for a FilterModel

    A tree of FilterItems can be stored by adding FilterItems recursively as children.
    Each FilterItem has a parent and a list of children.
    see https://doc.qt.io/qt-5/qtwidgets-itemviews-simpletreemodel-example.html

    Attributes:
        parent(FilterItem): item's parent
        children(list[FilterItem]): list of children
        data(any): str (logicType) or tuple/list (ConditionType).
        uuid(str):
        checked(boolean):
        type(FilterItem.LOGIC_TYPE/FilterItem.CONDITION_TYPE): Type of filter item.

    Examples:
        root = FilterItem() # Create rootItem
        root.append(FilterItem()) # Append 2 children
        root.append(FilterItem())
        root[0].append(FilterItem()) # Append 1 child to the first children
    """

    LOGIC_TYPE = 0  # Logic type is AND/OR
    CONDITION_TYPE = 1  # Condition type is (field, operator, value)

    def __init__(self, data=None, parent=None):
        """FilterItem constructor with parent as FilterItem parent

        Args:
            data(any): str (logicType) or tuple/list (ConditionType).
            parent (FilterItem): item's parent
        """
        # Item Type handling
        is_tuple = isinstance(data, (tuple, list))
        assert is_tuple or isinstance(data, str)
        self.data = list(data) if is_tuple else data
        self.type = self.CONDITION_TYPE if is_tuple else self.LOGIC_TYPE
        # Misc
        self.parent = parent
        self.children = []
        self.uuid = str(uuid.uuid1())
        self.checked = True

    def __del__(self):
        """Clear children (list[FilterItem])"""
        self.children.clear()

    def __repr__(self):
        return f"Filter Item {self.data}"

    def __getitem__(self, row):
        """Return FilterItem at the given index

        Args:
            row (int): child position

        Returns:
            FilterItem
        """
        return self.children[row]

    def append(self, item):
        """Append FilterItem child

        Args:
            item (FilterItem)
        """
        item.parent = self
        self.children.append(item)

    def insert(self, row: int, item):
        """Insert FilterItem child at a specific location

        Args:
            row (int): child index
            item (FilterItem)
        """
        item.parent = self
        self.children.insert(row, item)

    def remove(self, row: int):
        """Remove FilterItem child from a specific position

        Args:
            row (int): child index
        """
        del self.children[row]

    def row(self) -> int:
        """Return item location from his parent.

        If the item has no parent, it returns 0

        Returns:
            int: item index
        """
        if self.parent is not None:
            return self.parent.children.index(self)
        return 0

    def setRecursiveChecked(self, checked=True):
        self.checked = checked
        for child in self.children:
            child.set_recursive_check_state(checked)

    def get_field(self):
        if self.type == self.CONDITION_TYPE:
            return self.data[0]

    def get_operator(self):
        if self.type == self.CONDITION_TYPE:
            return self.data[1]

    def get_value(self):
        """Get value of condition or operator value

        Returns:
            - If item is a LOGIC_FIELD, return the operator AND/OR.
            - If item is a CONDITION_TYPE, return the value of the condition (last field).

        Examples:
            For a CONDITION_TYPE FilterItem: `("chr", "IN", (10, 11))`,
            this function will return `(10, 11)`.
        """
        if self.type == self.CONDITION_TYPE:
            return self.data[2]

        if self.type == self.LOGIC_TYPE:
            return self.data

    # def get_data(self, column=0):
    #     """ get data according columns.

    #     if item is a LOGIC_FIELD, it return self.data not matter the column.
    #     If item is a CONDITION_TYPE, you can select value from tuple according columns.

    #     column 0: Field name
    #     column 1: Field operator
    #     column 2 : Field value
    #     Args:
    #         column (int)

    #     Returns:
    #         (any): Data
    #     """

    #     if column == 0:
    #         return self.checked

    #     # if column == 1 or column == 2 or column == 3:
    #     #     if self.type == self.LOGIC_TYPE:
    #     #         return self.data

    #     #     if self.type == self.CONDITION_TYPE:
    #     #         return self.data[column - 1]

    def set_field(self, value):
        """Set field part of CONDITION_TYPE item"""
        if self.type == self.CONDITION_TYPE:
            self.data[0] = value

    def set_operator(self, value):
        """Set operator part of CONDITION_TYPE item"""
        if self.type == self.CONDITION_TYPE:
            self.data[1] = value

    def set_value(self, value):
        """Set value part of CONDITION_TYPE item or value of LOGIC_TYPE item

        Called when a user validates the editor.
        """
        if self.type == self.CONDITION_TYPE:
            self.data[2] = value
            return

        # LOGIC_TYPE:
        self.data = value


class FilterWidget(QWidget):
    def __init__(self, conn: sqlite3.Connection, parent: QWidget = None):
        super().__init__(parent)

        self.field_edit = ComboFieldEditor()
        self.field_edit.set_editable(True)
        self.field_edit.combo_box.currentTextChanged.connect(self._on_field_changed)
        self.setWindowTitle("Create filter")
        self.field_factory = FieldFactory(conn)

        self.operator_box = OperatorFieldEditor()
        self.operator_box.fill()

        self.field_edit.combo_box.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred)

        self.operator_box.combo_box.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred)

        self.form_layout = QFormLayout()
        self.form_layout.addRow("Field", self.field_edit)
        self.form_layout.addRow("Operator", self.operator_box)
        self.setLayout(self.form_layout)
        self.field_edit.fill(prepare_fields(conn))

    def set_field(self, field: str):
        self.field_edit.set_value(field)

    def set_filter(self, data: dict):
        item = FiltersModel.to_item(data)
        self.field_edit.set_value(item.get_field())
        self.operator_box.set_value(item.get_operator())
        self.value_edit.set_value(item.get_value())

    def get_filter(self) -> dict:

        field = self.field_edit.get_value()
        operator = self.operator_box.get_value()
        value = self.value_edit.get_value()

        return {field: {operator: value}}

    def _on_field_changed(self):

        # Remove previous
        if self.form_layout.rowCount() == 3:
            self.form_layout.removeRow(2)

        current_field = self.field_edit.get_value()
        self.value_edit = self.field_factory.create(current_field)

        self.form_layout.addRow("Value", self.value_edit)


class FilterDialog(QDialog):
    def __init__(self, conn: sqlite3.Connection, parent: QWidget = None):
        super().__init__(parent)

        self.widget = FilterWidget(conn)
        self.btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)

        self.btn_box.accepted.connect(self.accept)
        self.btn_box.rejected.connect(self.reject)

        vLayout = QVBoxLayout(self)
        vLayout.addWidget(self.widget)
        vLayout.addStretch()
        vLayout.addWidget(self.btn_box)

        self.setWindowTitle(self.widget.windowTitle())
        self.setFixedSize(self.sizeHint())

    def get_filter(self):
        return self.widget.get_filter()

    def set_filter(self, filter):
        self.widget.set_filter(filter)

    def set_field(self, field: str):
        self.widget.set_field(field)


class FiltersModel(QAbstractItemModel):
    """Model to display filter

    The model store filters as a nested tree of FilterItem.
    You can access set and get filters with self.set_filters() and self.get_filters().
    add_logic_item and add_condition_item, remove_item is used to edit the tree.

    Attributes:
        conn (sqlite3.connection): sqlite3 connection

    Additional roles:
        TypeRole: Items types (LOGIC_TYPE or CONDITION_TYPE)
        UniqueIdRole: Uuid of items.

    Signals:
        filtersChanged: Emitted when model data (filters) is changed.

    Examples:
        data = {"$and": [
        {"ref": "A"},
        {
            "$or": [
                {"chr":"chr5"},
                {"chr":"chr3"},
            ]
        },}}
        model = FilterModel(conn)
        model.set_filters(data)
        view = QTreeView()
        view.setModel(model)

        # Access item
        item  = model.item(view.currentIndex())
        # Add new item
        model.add_logic_item(parent = view.currentIndex())
        # Remove item
        model.remove_item(view.currentIndex())
    """

    # See self.headerData()
    _HEADERS = ["field", "operator", "value", "", ""]

    # Custom type to get FilterItem.type. See self.data()
    TypeRole = Qt.UserRole + 1
    UniqueIdRole = Qt.UserRole + 2

    filtersChanged = Signal()

    def __init__(self, conn: sqlite3.Connection = None, parent: QObject = None):
        super().__init__(parent)
        self.__root_item = FilterItem("$and")
        self.conn = conn
        self.clear()

    def get_filters(self) -> dict:
        """Return filters

        Returns:
            dict: filters fict
        """
        return self._to_dict()

    def set_filters(self, filters: dict):
        """Set filters and load the models

        Args:
            filters (dict)
        """
        self._from_dict(filters)

    def __del__(self):
        """Model destructor."""
        del self.__root_item

    def data(self, index: QModelIndex, role=Qt.EditRole) -> typing.Any:
        """Overrided Qt methods : Return model's data according index and role

        Warning:
            FilterDelegate.createEditor and setEditorData must use UserRole!
            The displayed elements are displayed from FilterItem with DisplayRole!
            Field* take ONLY UserRoles and convert them into something that can be
            showed to a user.

        Args:
            index (QModelIndex): index of item
            role (Qt.Role)

        Returns:
            Any type: Return value
        """
        if not index.isValid():
            return
        if index == QModelIndex():
            return

        item = self.item(index)
        val = item.get_value()

        # DECORATION ROLE
        if role == Qt.DecorationRole:
            if index.column() == COLUMN_CHECKBOX:
                return QIcon(FIcon(0xF06D0)) if item.checked else QIcon(FIcon(0xF06D1))

            if index.column() == COLUMN_FIELD and item.type == FilterItem.LOGIC_TYPE:
                if item.get_value() == "$and":
                    return QIcon(FIcon(0xF08E1))
                if item.get_value() == "$or":
                    return QIcon(FIcon(0xF08E5))

            if index.column() == COLUMN_FIELD and item.type == FilterItem.CONDITION_TYPE:

                return QIcon(FIcon(0xF044A, QApplication.style().colors().get("blue", "white")))

            if index.column() == COLUMN_REMOVE:
                if index.parent() != QModelIndex():
                    col = QApplication.style().colors().get("red", "red")
                    return QIcon(FIcon(0xF0156, col))

        # FONT ROLE
        if role == Qt.FontRole:
            if index.column() == COLUMN_FIELD:
                font = QFont()
                font.setBold(True)
                return font

            if index.column() == COLUMN_VALUE and val is None:
                font = QFont()
                font.setItalic(True)
                font.setBold(True)
                return font

        # FORGROUND ROLE
        if role == Qt.ForegroundRole:
            if not item.checked:
                color = QApplication.palette().color(QPalette.Disabled, QPalette.Text)
                return color

        # align operator
        if role == Qt.TextAlignmentRole:
            if index.column() == COLUMN_OPERATOR:
                return Qt.AlignHCenter + Qt.AlignVCenter

        # Role display or edit
        if role in (Qt.DisplayRole, Qt.EditRole):
            if index.column() == COLUMN_FIELD:
                if item.type == FilterItem.CONDITION_TYPE:
                    return item.get_field()

                if item.type == FilterItem.LOGIC_TYPE:
                    val = item.get_value()
                    return PY_TO_VQL_OPERATORS.get(val, "$and") + f"  ({len(item.children)})"

            if item.type != FilterItem.CONDITION_TYPE:
                return

            if index.column() == COLUMN_OPERATOR:
                operator = item.get_operator()
                return OPERATOR_VQL_TO_NAME.get(operator, "=")

            if index.column() == COLUMN_VALUE:
                val = item.get_value()
                if isinstance(val, list):
                    return ",".join(val)

                if isinstance(val, dict):
                    if "$wordset" in val:
                        return val["$wordset"]

                if val is None and role == Qt.DisplayRole:
                    return NULL_REPR

                return val

        if role == FiltersModel.TypeRole:
            # Return item type
            return item.type

        if role == FiltersModel.UniqueIdRole:
            return item.uuid

        return

    def setData(self, index, value, role=Qt.UserRole) -> bool:
        """Overrided Qt methods: Set value of FilterItem present at the given index.

        This method is called from FilterDelegate when edition has been done.

        Warning:
            FilterDelegate.createEditor and setEditorData must use UserRole!
            The displayed elements are displayed from FilterItem with DisplayRole!
            Field* take ONLY UserRoles and convert them into something that can be
            showed to a user.

        Args:
            index (QModelIndex)
            value (any): new value
            role (Qt.ItemDataRole): Qt.UserRole or Qt.CheckStateRole

        Returns:
            bool: Return True if success otherwise return False
        """
        if not index.isValid():
            return False

        if role in (Qt.DisplayRole, Qt.EditRole, Qt.UserRole):
            item = self.item(index)

            if index.column() == COLUMN_CHECKBOX:
                item.checked = bool(value)

            if index.column() == COLUMN_FIELD:
                if item.type == FilterItem.LOGIC_TYPE:
                    item.set_value(value)

                if item.type == FilterItem.CONDITION_TYPE:
                    item.set_field(value)

            if item.type == FilterItem.CONDITION_TYPE:

                if index.column() == COLUMN_OPERATOR:
                    item.set_operator(value)

                if index.column() == COLUMN_VALUE:
                    item.set_value(value)

            self.filtersChanged.emit()
            # just one item is changed
            self.dataChanged.emit(index, index, role)
            return True

        if role == Qt.CheckStateRole and index.column() == COLUMN_CHECKBOX:
            self.set_recursive_check_state(index, bool(value))
            self.filtersChanged.emit()
            # just one item is changed
            self.dataChanged.emit(index, index, role)
            return True

        return False

    def headerData(self, section, orientation, role=Qt.DisplayRole) -> typing.Any:
        """Return header data

        Args:
            section (integer): row
            orientation (Qt.Orientation): Vertical or horizontal header
            role (Qt.ItemDataRole, optional): data role

        Returns:
            Any type of data
        """
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return self._HEADERS[section]

        if role == Qt.TextAlignmentRole:
            if orientation == Qt.Horizontal:
                if section == COLUMN_FIELD:
                    return Qt.AlignLeft
                if section == COLUMN_OPERATOR:
                    return Qt.AlignCenter
                if section == COLUMN_VALUE:
                    return Qt.AlignLeft

    def is_last(self, index: QModelIndex()) -> bool:
        """Return True if index is the last in the row
        This is used by draw_branch
        """
        if index == QModelIndex():
            return False

        return index.row() == index.model().rowCount(index.parent()) - 1

    def index(self, row, column, parent=QModelIndex()) -> QModelIndex:
        """Overrided Qt methods: create index according row, column and parent

        Usefull for dataChanged signal

        Returns:
            QModelIndex
        """
        if not self.hasIndex(row, column, parent):
            return QModelIndex()

        if not parent.isValid():  # If no parent, then parent is the root item
            parent_item = self.__root_item

        else:
            parent_item = parent.internalPointer()

        child_item = parent_item[row]
        if child_item:
            return self.createIndex(row, column, child_item)
        else:
            return QModelIndex()

    def parent(self, index: QModelIndex) -> QModelIndex:
        """Overrided Qt methods: Create parent from index"""
        if not index.isValid():
            return QModelIndex()

        child_item = index.internalPointer()

        parent_item = child_item.parent

        if parent_item == self.__root_item:
            return QModelIndex()

        return self.createIndex(parent_item.row(), 0, parent_item)

    def clear(self):
        """Clear Model"""
        self.beginResetModel()
        self.__root_item.children.clear()
        # Load first default item
        self.__root_item.append(FilterItem("$and"))

        self.endResetModel()

    def _from_dict(self, data: dict):
        """load model from dict

        dict should be a nested dictionnary of condition. For example:
        data = {"$and": [
        {"ref":"A"},
        {
            "$or": [
                {"chr":"chr5"},
                {"chr":"chr3"},
            ]
        },}}
        Args:
            data (TYPE): Description
        """
        self.beginResetModel()
        if data:
            self.__root_item.children.clear()
            self.__root_item.append(FiltersModel.to_item(data))
        self.endResetModel()

    @classmethod
    def _is_logic(cls, item: dict) -> bool:
        """
        Returns whether item holds a logic operator
        Example:
            > _is_logic({"$and":[...]})
            > True
        """
        keys = list(item.keys())
        return keys[0] in ("$and", "$or")

    @classmethod
    def to_item(cls, data: dict) -> FilterItem:
        """Recursive function to build a nested FilterItem structure from dict data"""
        if cls._is_logic(data):
            operator = list(data.keys())[0]
            item = FilterItem(operator)
            [item.append(cls.to_item(k)) for k in data[operator]]
        else:  # condition item

            field = list(data.keys())[0]
            value = data[field]
            operator = "$eq"

            if isinstance(value, dict):
                k, v = list(value.items())[0]
                operator = k
                value = v

            item = FilterItem((field, operator, value))

        return item

    def _to_dict(
        self,
        item: FilterItem = None,
        checked_only: bool = True,
    ) -> dict:
        """Recursive function to build a nested dictionnary from FilterItem structure

        Args:
            item (FilterItem, optional): Top-most item to get the dict of. If None, root item is chosen. Defaults to None.
            checked_only (bool, optional): Only select items that are checked. Defaults to True.

        Returns:
            dict: [description]

        Note:
            We use data from FilterItems; i.e. the equivalent of UserRole data.
        """

        if len(self.__root_item.children) == 0:
            return {}

        if item is None:
            item = self.__root_item[0]

        if checked_only:
            if item.type == FilterItem.LOGIC_TYPE and item.checked is True:
                # Return dict with operator as key and item as value
                operator_data = [
                    self._to_dict(child) for child in item.children if child.checked is True
                ]
                return {item.get_value(): operator_data}
        else:
            if item.type == FilterItem.LOGIC_TYPE:
                # Return dict with operator as key and item as value
                operator_data = [self._to_dict(child) for child in item.children]
                return {item.get_value(): operator_data}

        if item.type == FilterItem.CONDITION_TYPE:
            result = {}
            operator = item.get_operator()
            if operator == "$eq":
                result = {item.get_field(): item.get_value()}
            else:
                result = {item.get_field(): {operator: item.get_value()}}
            return result

    def add_logic_item(self, value="$and", parent=QModelIndex()):
        """Add logic item

        Args:
            value (str): Can be "AND" or "OR"
            parent (QModelIndex): parent index
        """

        #  Skip if parent is a condition type
        if self.item(parent).type == FilterItem.CONDITION_TYPE:
            return

        self.beginInsertRows(parent, 0, 0)
        self.item(parent).insert(0, FilterItem(data=value))
        self.endInsertRows()
        self.filtersChanged.emit()

    def add_condition_item(self, value=("ref", "$eq", "A"), parent=QModelIndex()):
        """Add condition item

        Args:
            value (tuple): Condition data (field, operator, value)
            parent (QModelIndex): Parent index
        """
        # Skip if parent is a condition type
        if self.item(parent).type == FilterItem.CONDITION_TYPE:
            return

        row = self.rowCount(parent)
        self.beginInsertRows(parent, row - 1, row - 1)
        item = FilterItem(data=value)
        self.item(parent).append(item)
        self.endInsertRows()
        self.filtersChanged.emit()

    def remove_item(self, index: QModelIndex):
        """Remove Item

        Args:
            index (QModelIndex): item index
        """
        if index.isValid():
            self.beginRemoveRows(index.parent(), index.row(), index.row())
            self.item(index).parent.remove(index.row())
            self.endRemoveRows()
            self.filtersChanged.emit()

    def rowCount(self, parent=QModelIndex()) -> int:
        """Overrided Qt methods: return row count according parent"""
        if parent.column() > 0:
            return 0

        if not parent.isValid():
            parent_item = self.__root_item
        else:
            parent_item = parent.internalPointer()

        return len(parent_item.children)

    def columnCount(self, parent=QModelIndex()) -> int:
        """Overrided Qt methods: return column count according parent"""

        return 5

    def flags(self, index) -> Qt.ItemFlags:
        """Overrided Qt methods: return Qt flags to make item editable and selectable"""

        if not index.isValid():
            return Qt.NoItemFlags

        item = index.internalPointer()

        if index.column() == COLUMN_CHECKBOX or index.column() == COLUMN_REMOVE:
            return Qt.ItemIsSelectable | Qt.ItemIsEnabled

        if item.type == FilterItem.LOGIC_TYPE and index.column() != COLUMN_FIELD:
            return Qt.ItemIsSelectable | Qt.ItemIsEnabled

        if item.type == FilterItem.LOGIC_TYPE and index.column() == COLUMN_FIELD:
            return (
                Qt.ItemIsSelectable
                | Qt.ItemIsEditable
                | Qt.ItemIsEnabled
                | Qt.ItemIsDragEnabled
                | Qt.ItemIsDropEnabled
            )

        if item.type == FilterItem.CONDITION_TYPE:
            return Qt.ItemIsSelectable | Qt.ItemIsEditable | Qt.ItemIsEnabled | Qt.ItemIsDragEnabled

        return Qt.ItemIsSelectable | Qt.ItemIsEditable | Qt.ItemIsEnabled

    def item(self, index: QModelIndex) -> FilterItem:
        """Return Filter Item from model index

        Args:
            index (QModelIndex)

        Returns:
            FilterItem
        """
        if index.isValid():
            return index.internalPointer()
        else:
            return self.__root_item

    def moveRow(
        self,
        sourceParent: QModelIndex,
        sourceRow: int,
        destinationParent: QModelIndex,
        destinationChild: int,
    ) -> bool:
        """Overrided Qt methods : Move an item from source to destination index
        Args:
            sourceParent (QModelIndex): parent of souce item
            sourceRow (int): index position of source item
            destinationParent (QModelIndex): parent od destination item
            destinationChild (int): index position of destination item

        Returns:
            bool: Return True if success otherwise retur False
        """
        parent_source_item = self.item(sourceParent)
        parent_destination_item = self.item(destinationParent)

        # Avoid segfault by returning False as soon as you are trying to drag drop the item on itself
        if sourceParent == destinationParent:
            return False
        #  if destination is - 1, it's mean we should append the item at the end of children
        if destinationChild < 0:
            destinationChild = len(parent_destination_item.children)

        # Don't move same same Item
        if sourceParent == destinationParent and sourceRow == destinationChild:
            return False

        self.beginMoveRows(sourceParent, sourceRow, sourceRow, destinationParent, destinationChild)
        item = parent_source_item.children.pop(sourceRow)
        parent_destination_item.insert(destinationChild, item)
        self.endMoveRows()

        self.filtersChanged.emit()
        return True

    def supportedDropActions(self) -> Qt.DropAction:
        """Overrided from Qt. Return supported drop action by the model

        Returns:
            Qt.DropAction
        """
        return Qt.MoveAction | Qt.CopyAction

    def _drop_filter(self, filter_dict: dict, parent: QModelIndex) -> bool:
        """Called when a drop operation contains raw, plain text

        Args:
            row (int): Row to drop filter_dict on
            filter_dict (dict): A dict representing a valid filter item. Either a tree or a single condition
            parent (QModelIndex): What index to drop filter_dict to

        Returns:
            bool: True if FilterItem was successfully added
        """
        try:
            item_ = FiltersModel.to_item(filter_dict)
        except Exception as e:
            # Invalid item
            return False
        if self.item(parent).type == FilterItem.LOGIC_TYPE:
            self.beginInsertRows(parent, self.rowCount(parent) - 1, self.rowCount(parent) - 1)
            self.item(parent).append(item_)
            self.endInsertRows()
            self.filtersChanged.emit()
            return True

        else:
            return False

    def _drop_condition(self, row: int, condition: dict, parent: QModelIndex) -> bool:
        """Called when a drop happens with cutevariant typed json data

        Args:
            row (int): Row to drop condition at
            condition (dict): condition to add in the following format: {"field":$field_name,"operator":$operator,"value":$value}
            parent (QModelIndex): Index on which the drop is performed at row *row*.

        Returns:
            bool: True if condition was successfully added
        """
        # First case: row is not valid (usually -1 when dropping on a parent logical item)
        if row < 0 or row > self.rowCount(parent):
            self.add_condition_item(
                (
                    condition.get("field", "chr"),
                    condition.get("operator", "$eq"),
                    condition.get("value", 7),
                ),
                parent,
            )
            self.filtersChanged.emit()
            return True

        # Second case: row is valid. Only replace operator and value from condition, not
        index = parent.child(row, 0)
        if index.isValid():
            # When we drop a condition, we don't want to change the field. Only condition and value
            self.item(index).set_operator(condition.get("operator", "$eq"))
            self.item(index).set_value(condition.get("value", 7))
            self.dataChanged.emit(index, index)
            self.filtersChanged.emit()
            return True
        return False

    def _drop_internal_move(
        self,
        source_coords: typing.List[int],
        destintation_parent: QModelIndex,
        destination_row: int,
    ) -> bool:
        """Special case where we drop a filter from self's tree. In that case, it comes from self's mimeData method.

        Args:
            source_coords (List[int]): List of integers (row numbers in tree, top to bottom) leading to the index that is being moved
            destintation_parent (QModelIndex): Where to drop the filter that was self-dragged
            destination_row (int):

        Returns:
            bool: True on success, False otherwise
        """
        if not source_coords:
            return False
        index = QModelIndex()
        # index is the modelindex of the item we want to move
        for row in source_coords:
            index = self.index(row, 0, index)
        if index.isValid():
            return self.moveRow(index.parent(), index.row(), destintation_parent, destination_row)
        return False

    def dropMimeData(self, data: QMimeData, action, row, column, parent: QModelIndex) -> bool:
        """Overrided Qt methods: This method is called when item is dropped by drag/drop.
        data is QMimeData and it contains a pickle serialization of current dragging item.
        Get back item by unserialize data.data().

        Args:
            data (QMimeData)
            action (Qt.DropAction)
            row (int): row destination
            column (int): column destination ( not used)
            parent (QModelIndex): parent destination

        Returns:
            bool: return True if success otherwise return False
        """

        if action != Qt.MoveAction and action != Qt.CopyAction:
            return False

        # Test for typed json first. This MIME type has higher precedence
        if data.hasFormat("cutevariant/typed-json"):
            obj = json.loads(str(data.data("cutevariant/typed-json"), "utf-8"))

            # The drop is a serialized object, we need to treat it differently than raw json
            if "type" in obj:
                # Special case where we need to know that the move is internal
                if obj["type"] == "internal_move":
                    if "coords" not in obj:
                        return False
                    return self._drop_internal_move(obj["coords"], parent, row)
                if obj["type"] == "fields":
                    if "fields" in obj:
                        fields = obj["fields"]
                        if isinstance(fields, list):
                            if row < 0 or row > self.rowCount(parent):
                                return self._drop_filter(
                                    {
                                        field_name: DEFAULT_VALUES.get(field_type, "")
                                        for field_name, field_type in fields
                                    },
                                    parent,
                                )
                if obj["type"] == "condition":
                    return self._drop_condition(row, obj["condition"], parent)
            return False

        # Test for URIs first since they are also plain text. However pure plain text is never uri-list so we should test uri-list first...
        if data.hasFormat("text/uri-list"):
            urls = data.urls()
            if urls:
                url: QUrl = urls[0]
                if url.isLocalFile():
                    with open(url.toLocalFile()) as f:
                        return self._drop_filter(json.load(f), parent)

        # Fallback if drop didn't contain neither typed json, nor URL. This assumes that the text you are trying to drop is a valid filter
        if data.hasFormat("text/plain"):
            try:
                return self._drop_filter(json.loads(data.text()), parent)
            except Exception as e:
                return False

        return False

    def mimeData(self, indexes: typing.List[QModelIndex]) -> QMimeData:
        """Serialize item from indexes into a QMimeData
        Currently, it serializes only the first index from t he list.
        Args:
            indexes (list<QModelIndex>)

        Returns:
            QMimeData
            ..see: self.dropMimeData
        """
        if not indexes:
            return

        mime_data = super().mimeData(indexes)
        parent = indexes[0]
        coords = []
        # Compute coords of index by recursively finding parent's row until root index.
        # First number in the list is the row among root parent children. Always 0, since there can be only one root as a logical operator
        while parent != QModelIndex():
            coords.insert(0, parent.row())
            parent = parent.parent()
        mime_data.setData(
            "cutevariant/typed-json",
            bytes(json.dumps({"type": "internal_move", "coords": coords}), "utf-8"),
        )

        return mime_data

    def set_recursive_check_state(self, index, checked=True):
        """Recursive check of all subfilters"""

        if not index.isValid():
            return

        item = self.item(index)

        item.checked = checked

        start = self.index(index.row(), 0, index.parent())
        end = self.index(index.row(), self.columnCount() - 1, index.parent())

        # Update specific changed item
        self.dataChanged.emit(start, end)

        for row in range(self.rowCount(index)):
            cindex = self.index(row, 0, index)
            self.set_recursive_check_state(cindex, checked)

    def mimeTypes(self) -> typing.List:
        return ["text/plain", "cutevariant/typed-json"]

    def canDropMimeData(
        self,
        data: QMimeData,
        action: Qt.DropAction,
        row: int,
        column: int,
        parent: QModelIndex,
    ) -> bool:

        # Ask your father (literally). Check if data is in supportedMimeData(), action in supportedActions() etc
        basic_answer = super().canDropMimeData(data, action, row, column, parent)

        if not basic_answer:
            return False

        dest_data = self.mimeData([self.index(row, column, parent)]).data("cutevariant/typed-json")
        source_data = data.data("cutevariant/typed-json")

        if dest_data == source_data:
            return False

        # dest_index = self.index(row, column, parent)
        # dest_data = self.mimeData([dest_index])
        obj = json.loads(str(data.data("cutevariant/typed-json").data().decode()))

        if "type" in obj:
            if obj["type"] == "internal_move":
                return True

            return True

        return True


class FiltersDelegate(QStyledItemDelegate):
    """FilterDelegate is used to create widget editor for the model inside the view.

    Notes:
        Without a delegate, the view cannot display editor when user double clicks
        on a cell.

        Editors are created from self.createEditor.
        FilterModel data are read and written respectively with setEditorData and
        setModelData.

        The view has 5 columns, enumerated with the following names:

        - COLUMN_CHECKBOX = 0
        - COLUMN_FIELD = 1
        - COLUMN_LOGIC = 1
        - COLUMN_OPERATOR = 2
        - COLUMN_VALUE = 3
        - COLUMN_REMOVE = 4

    Examples:
        view = QTreeView()
        model = FilterModel()
        delegate = FilterDelegate()
        view.setModel(model)
        view.setItemDelegate(delegate)
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.add_icon = FIcon(0xF0704)
        self.group_icon = FIcon(0xF0704)
        self.rem_icon = FIcon(0xF0235, "red")

        self.eye_on = FIcon(0xF0208)
        self.eye_off = FIcon(0xF0209)

        s = QApplication.style().pixelMetric(QStyle.PM_ListViewIconSize)
        self.icon_size = QSize(s, s)
        self.row_height = QApplication.style().pixelMetric(QStyle.PM_ListViewIconSize) * 1.2

    def createEditor(self, parent, option, index: QModelIndex) -> QWidget:
        """Overrided from Qt. Create an editor for the selected column.

        The editor is based on the selected column and on the type of FilterItem
        (LOGIC_TYPE or CONDITION_TYPE). It is also based on the selected SQL field,
        and on the SQL operator.

        Args:
            parent (QWidget): widget's parent
            option (QStyleOptionViewItem)
            index (QModelIndex)

        Returns:
            QWidget: a editor with set_value and get_value methods
        """
        model = index.model()
        item = model.item(index)
        field = item.get_field()
        operator = item.get_operator()

        factory = FieldFactory(model.conn)

        # Get current sql connection
        # conn = model.conn

        if index.column() == COLUMN_FIELD:
            if item.type == FilterItem.LOGIC_TYPE:
                return LogicFieldEditor(parent)
            if item.type == FilterItem.CONDITION_TYPE:
                combo = ComboFieldEditor(parent)
                combo.set_editable(True)
                combo.fill(prepare_fields(model.conn))
                return combo

        if index.column() == COLUMN_OPERATOR:
            w = OperatorFieldEditor(parent)
            # Fill operator according fields
            field_type = factory.field_types_mapping[field]
            w.fill()
            return w

        if index.column() == COLUMN_VALUE:
            # TODO: create instance only one time
            w = factory.create(field, operator, parent)
            return w

    def setEditorData(self, editor: QWidget, index: QModelIndex):

        model = index.model()
        item = model.item(index)
        field = item.get_field()
        operator = item.get_operator()
        value = item.get_value()

        if index.column() == COLUMN_VALUE:
            editor.set_value(value)

        if index.column() == COLUMN_OPERATOR:
            editor.set_value(operator)

        if index.column() == COLUMN_FIELD:
            editor.set_value(field)

    def editorEvent(self, event: QEvent, model, option, index: QModelIndex):
        """

        When editing of an item starts, this function is called with the event
        that triggered the editing, the model, the index of the item, and the
        option used for rendering the item.

        Mouse events are sent to editorEvent() even if they don't start editing
        of the item.

        This is used here to act on COLUMN_CHECKBOX and COLUMN_REMOVE

        Args:
            event:
            model:
            option:
            index:

        Returns:
            (boolean): True if event is accepted; False otherwise.

        """
        if not index.isValid():
            return False

        # Skip action with First LogicItem root item

        if event.type() == QEvent.MouseButtonPress:

            item = model.item(index)

            if index.column() == COLUMN_CHECKBOX and option.rect.contains(event.pos()):
                # Invert check state
                model.setData(index, not item.checked, role=Qt.CheckStateRole)
                return True

            if index.column() == COLUMN_REMOVE and option.rect.contains(event.pos()):
                # Remove item

                # Do not remove first elements
                if index.parent() != QModelIndex():
                    model.remove_item(index)
                return True

        # Default implementation of base method
        return False

    def setModelData(self, editor, model, index):
        """Overrided from Qt: Update the model with data from the editor.

        Currently, it calls model.setData()

        See Also:
            :meth:`setModelData` for the opposite function (set editor data)

        Args:
            editor (QWidget): editor
            model (FilterModel)
            index (QModelindex)
        """

        if index.column() == COLUMN_FIELD:

            # Change operator and value
            mapping = prepare_fields(model.conn)
            field_name = editor.get_value()
            field_type = mapping.get(field_name, "str")
            operator_index = model.index(index.row(), COLUMN_OPERATOR, index.parent())
            value_index = model.index(index.row(), COLUMN_VALUE, index.parent())

            model.setData(operator_index, "$eq")
            model.setData(index, editor.get_value())
            model.setData(value_index, DEFAULT_VALUES.get(field_type, ""))

        else:
            model.setData(index, editor.get_value())

        # super().setModelData(editor, model, index)

    # def _compute_width(self, index):

    #     if index.isValid():
    #         font = QFont()
    #         metric = QFontMetrics(font)
    #         return metric.width(str(index.data(Qt.DisplayRole)))

    #     return 50

    def sizeHint(self, option, index: QModelIndex) -> QSize:
        """Overrided from Qt. Return size of row

        Args:
            option (QStyleOptionViewItem )
            index (QModelIndex)

        Returns:
            TYPE: Description
        """

        size = QSize(option.rect.width(), self.row_height)

        # if index.column() == COLUMN_CHECKBOX:
        #     return QSize(20, 30)

        # if index.column() == COLUMN_OPERATOR:
        #     return QSize(20, 30)

        # if index.column() == COLUMN_FIELD:
        #     margin = self.indentation * self._compute_level(index) + self.indentation
        #     size.setWidth(size.width() + margin + 10)

        return size

    def _compute_level(self, index: QModelIndex):
        level = 0
        i = index.parent()
        while i.isValid():
            i = i.parent()
            level += 10

        return level

        # painter.setPen(option.palette.color(QPalette.Dark))

        # painter.setPen(QPen(QColor("lightgray")))

        # item = index.model().item(index)

        # if item.type == FilterItem.CONDITION_TYPE or index.column() == COLUMN_VALUE:
        #     painter.drawLine(option.rect.topRight(), option.rect.bottomRight())

        # if index.column() == 0:
        #     painter.drawLine(QPoint(0, option.rect.bottom()), option.rect.bottomRight())
        # else:
        #     painter.drawLine(option.rect.bottomLeft(), option.rect.bottomRight())

    def paint(self, painter, option, index):

        # ======== Draw background
        item = index.model().item(index)
        is_selected = False

        if option.state & QStyle.State_Enabled:
            bg = (
                QPalette.Normal
                if option.state & QStyle.State_Active or option.state & QStyle.State_Selected
                else QPalette.Inactive
            )
        else:
            bg = QPalette.Disabled

        if option.state & QStyle.State_Selected:
            is_selected = True
            painter.fillRect(option.rect, option.palette.color(bg, QPalette.Highlight))

        #     # margin = self.indentation * (self._compute_level(index))

        #  ========= Draw icon centered
        if index.column() == COLUMN_CHECKBOX or index.column() == COLUMN_REMOVE:

            decoration_icon = index.data(Qt.DecorationRole)

            if decoration_icon:
                rect = QRect(0, 0, option.decorationSize.width(), option.decorationSize.height())
                rect.moveCenter(option.rect.center())
                # rect.setX(4)
                painter.drawPixmap(
                    rect.x(), rect.y(), decoration_icon.pixmap(option.decorationSize)
                )

        else:
            super().paint(painter, option, index)

        # Draw lines

        painter.setPen(Qt.NoPen)
        if (
            item.type == FilterItem.CONDITION_TYPE
            or index.column() == COLUMN_VALUE
            or index.column() == COLUMN_CHECKBOX
        ):
            painter.drawLine(option.rect.topRight(), option.rect.bottomRight())

        if index.column() == 0:
            painter.drawLine(QPoint(0, option.rect.bottom()), option.rect.bottomRight())
        else:
            painter.drawLine(option.rect.bottomLeft(), option.rect.bottomRight())

    # if index.column() > COLUMN_CHECKBOX:

    #     if index.column() == 1:
    #         self._draw_branch(painter, option, index)
    #     # pen = QPen(QColor("white"), 1, Qt.DotLine)
    #     # painter.setPen(pen)
    #     # # painter.drawRect(option.rect)
    #     # painter.drawLine(
    #     #     option.rect.left(),
    #     #     option.rect.center().y(),
    #     #     margin - 2,
    #     #     option.rect.center().y(),
    #     # )

    #     # painter.drawLine(
    #     #     option.rect.left(),
    #     #     option.rect.top(),
    #     #     option.rect.left(),
    #     #     option.rect.bottom(),
    #     # )

    #     font = QFont()
    #     align = Qt.AlignVCenter
    #     color = option.palette.color(
    #         QPalette.Normal if item.checked else QPalette.Disabled,
    #         QPalette.HighlightedText if is_selected else QPalette.WindowText,
    #     )

    #     if (
    #         item.type == FilterItem.LOGIC_TYPE
    #         and index.column() == COLUMN_FIELD
    #     ):
    #         font.setBold(True)
    #         # metric = QFontMetrics(font)
    #         # print(self._compute_level(index))
    #         # text_width = metric.boundingRect(index.data()).width()
    #         # #  Draw Add buttion
    #         # rect = QRect(0, 0, self.icon_size.width(), self.icon_size.height())
    #         # rect.moveCenter(
    #         #     QPoint(
    #         #         option.rect.x() + margin + text_width + 20,
    #         #         option.rect.center().y(),
    #         #     )
    #         # )
    #         # painter.drawPixmap(
    #         #     rect.right() - self.icon_size.width(),
    #         #     rect.y(),
    #         #     self.add_icon.pixmap(self.icon_size),
    #         # )
    #     if index.column() == COLUMN_FIELD:
    #         align |= Qt.AlignLeft

    #     if index.column() == COLUMN_OPERATOR:
    #         align |= Qt.AlignCenter

    #     if index.column() == COLUMN_VALUE:
    #         align |= Qt.AlignLeft

    #     painter.setFont(font)
    #     painter.setPen(color)
    #     # Indentation level

    #     text_rect = option.rect
    #     if index.column() == 1:
    #         xstart = option.rect.x() + margin
    #         text_rect.setX(xstart)

    #     painter.drawText(text_rect, align, index.data(Qt.DisplayRole))

    #     if index.column() == COLUMN_REMOVE and index.parent() != QModelIndex():
    #         rect = QRect(0, 0, self.icon_size.width(), self.icon_size.height())
    #         rect.moveCenter(option.rect.center())
    #         painter.drawPixmap(
    #             rect.right() - self.icon_size.width(),
    #             rect.y(),
    #             self.rem_icon.pixmap(self.icon_size),
    #         )

    # if index.column() == 3:
    #     painter.drawPixmap(self._icon_rect(option), self.rem_icon.pixmap(self.icon_size))

    # if index.column() == 3 and item.type == FilterItem.LOGIC_TYPE:
    #     x = option.rect.right() - 20
    #     y = option.rect.center().y() - self.icon_size.height() / 2
    #     painter.drawPixmap(QRect(x,y,self.icon_size.width(), self.icon_size.height()), self.add_icon.pixmap(self.icon_size))

    # super().paint(painter, option,index)

    def _icon_rect(self, rect):
        x = rect.x()
        y = rect.center().y() - self.icon_size.height() / 2

        return QRect(x, y, self.icon_size.width(), self.icon_size.height())

    def _check_rect(self, rect):
        return QRect(rect.x(), rect.y(), rect.height(), rect.height())

    def updateEditorGeometry(self, editor, option, index):
        """Overrided from Qt. Set editor geometry

        Args:
            editor (QWidget)
            option (QStyleOptionViewItem)
            index (QModelIndex)
        """

        if index.column() == COLUMN_VALUE:
            option.rect.setHeight(self.row_height - 1)
            editor.setGeometry(option.rect)
            return

        super().updateEditorGeometry(editor, option, index)


class FiltersWidget(QTreeView):
    def __init__(self, conn=None, parent=None):
        super().__init__()

        self._model = FiltersModel(conn)
        self._delegate = FiltersDelegate()
        self.setModel(self._model)
        self.setItemDelegate(self._delegate)

        self.setIndentation(10)
        self.setExpandsOnDoubleClick(False)
        self.setAlternatingRowColors(True)
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDragDropMode(QAbstractItemView.DragDrop)

        self.header().setStretchLastSection(False)
        self.header().setSectionResizeMode(COLUMN_FIELD, QHeaderView.Interactive)
        self.header().setSectionResizeMode(COLUMN_OPERATOR, QHeaderView.Interactive)
        self.header().setSectionResizeMode(COLUMN_VALUE, QHeaderView.Stretch)
        self.header().setSectionResizeMode(COLUMN_CHECKBOX, QHeaderView.ResizeToContents)
        self.header().setSectionResizeMode(COLUMN_REMOVE, QHeaderView.ResizeToContents)
        self.setEditTriggers(QAbstractItemView.DoubleClicked)

        # self.selectionModel().selectionChanged.connect(self.on_selection_changed)

    def set_filters(self, filters: dict):
        self._model.set_filters(filters)

    def get_filters(self) -> dict:
        return self._model.get_filters()

    def clear_cache(self):
        prepare_fields.cache_clear()
        get_field_unique_values_cached.cache_clear()


if __name__ == "__main__":
    from cutevariant.core import sql

    from tests import utils

    app = QApplication(sys.argv)

    conn = utils.create_conn("/home/sacha/Dev/cutevariant/examples/test.snpeff.vcf")

    # conn = sql.get_sql_connection("/home/sacha/Dev/cutevariant/examples/strasbouirg.db")
    # data = {
    #     "$and": [
    #         {"chr": "chr12"},
    #         {"ref": "chr12"},
    #         {"ann.gene": "chr12"},
    #         {"ann.gene": "chr12"},
    #         {"pos": 21234},
    #         {"favorite": True},
    #         {"qual": {"$gte": 40}},
    #         {"ann.gene": {"$in": ["CFTR", "GJB2"]}},
    #         {"qual": {"$in": {"$wordset": "boby"}}},
    #         {"qual": {"$nin": {"$wordset": "boby"}}},
    #         {"samples.boby.gt": 1},
    #         {
    #             "$and": [
    #                 {"ann.gene": "chr12"},
    #                 {"ann.gene": "chr12"},
    #                 {"$or": [{"ann.gene": "chr12"}, {"ann.gene": "chr12"}]},
    #             ]
    #         },
    #     ]
    # }
    # view = FiltersWidget(conn)
    # view.set_filters(data)

    view = FilterDialog(conn)

    view.show()

    app.exec()
