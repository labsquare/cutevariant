# Standard imports
import re
from cutevariant.gui.mainwindow import MainWindow
from cutevariant.config import Config
from logging import Filter
import sys
import json
import os
import pickle
import typing
import uuid
from ast import literal_eval
from functools import lru_cache
from typing import Any, Iterable
import sqlite3
import glob

# Qt imports
from PySide2.QtWidgets import (
    QInputDialog,
    QWidget,
    QTreeView,
    QFrame,
    QToolButton,
    QPushButton,
    QCompleter,
    QStackedWidget,
    QDialog,
    QLineEdit,
    QActionGroup,
    QFileDialog,
    QApplication,
    QStyledItemDelegate,
    QToolBar,
    QAbstractItemView,
    QHeaderView,
    QComboBox,
    QSizePolicy,
    QMessageBox,
    QHBoxLayout,
    QVBoxLayout,
    QMenu,
    QStyle,
    QAbstractItemDelegate,
    QAction,
)
from PySide2.QtCore import (
    QAbstractListModel,
    QUrl,
    Qt,
    QObject,
    Signal,
    Slot,
    QDir,
    QAbstractItemModel,
    QModelIndex,
    QMimeData,
    QEvent,
    QStandardPaths,
    QStringListModel,
    QSize,
    QByteArray,
    QFileInfo,
    QSettings,
    QRect,
)
from PySide2.QtGui import (
    QMouseEvent,
    QPainter,
    QPalette,
    QFont,
    QPen,
    QBrush,
    QIcon,
    QIntValidator,
    QDoubleValidator,
    QKeySequence,
    QContextMenuEvent,
    QStandardItemModel,
)

# Custom imports
from cutevariant.gui import style, plugin, FIcon
from cutevariant.core import sql, get_sql_connection
from cutevariant.core.vql import parse_one_vql
from cutevariant.core.querybuilder import (
    build_vql_query,
    fields_to_vql,
)
import cutevariant.commons as cm
from cutevariant.gui.sql_thread import SqlThread

from cutevariant import LOGGER

# TYPE_OPERATORS = {
#     "str": ["$eq", "$ne", "$in", "$nin", "$regex", "$has"],
#     "float": ["$eq", "$ne", "$gte", "$gt", "$lt", "$lte"],
#     "int": ["$eq", "$ne", "$gte", "$gt", "$lt", "$lte"],
#     "bool": ["$eq"],
# }


OPERATORS = [
    "$eq",
    "$ne",
    "$in",
    "$nin",
    "$regex",
    "$has",
    "$gte",
    "$gt",
    "$lt",
    "$lte",
]


DEFAULT_VALUES = {"str": "", "int": 0, "float": 0.0, "list": [], "bool": True}

OPERATORS_PY_VQL = {
    "$eq": "=",
    "$gt": ">",
    "$gte": ">=",
    "$lt": "<",
    "$lte": "<=",
    "$in": "IN",
    "$ne": "!=",
    "$nin": "NOT IN",
    "$regex": "~",
    "$and": "AND",
    "$or": "OR",
    "$has": "HAS",
}

NULL_REPR = "@NULL"


COLUMN_FIELD = 0
COLUMN_LOGIC = 0
COLUMN_OPERATOR = 1
COLUMN_VALUE = 2
COLUMN_CHECKBOX = 3
COLUMN_REMOVE = 4


@lru_cache()
def get_field_unique_values_cached(conn, field, like, limit):
    print("cache me ")
    return sql.get_field_unique_values(conn, field, like, limit)


@lru_cache()
def prepare_fields(conn):
    """Prepares a list of columns on which filters can be applied"""
    results = {}
    samples = [sample["name"] for sample in sql.get_samples(conn)] + ["*"]

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


##------------PRESETS


class FiltersPresetModel(QAbstractListModel):
    def __init__(self, config_path=None, parent: QObject = None) -> None:
        super().__init__(parent=parent)
        self.config_path = config_path
        self._presets = []

    def data(self, index: QModelIndex, role: int) -> typing.Any:
        if role == Qt.DisplayRole or role == Qt.EditRole:
            if index.row() >= 0 and index.row() < self.rowCount():
                return self._presets[index.row()][0]
        if role == Qt.UserRole:
            if index.row() >= 0 and index.row() < self.rowCount():
                return self._presets[index.row()][1]

        return

    def setData(self, index: QModelIndex, value: str, role: int) -> bool:
        """Renames the preset
        The content is read-only from the model's point of view

        Args:
            index (QModelIndex): [description]
            value (str): [description]
            role (int): [description]

        Returns:
            bool: True on success
        """
        if role == Qt.EditRole:
            self._presets[index.row()] = (value, self._presets[index.row()][1])
            return True
        else:
            return False

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        if not index.isValid():
            return Qt.NoItemFlags
        return super().flags(index) | Qt.ItemIsEditable

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._presets)

    def add_preset(self, name: str, filter: dict):
        """Add filter preset

        Args:
            name (str): preset name
            filter (dict): one filter dict
        """
        self.beginInsertRows(QModelIndex(), 0, 0)
        self._presets.insert(0, (name, filter))
        self.endInsertRows()

    def rem_presets(self, indexes: typing.List[int]):
        indexes.sort(reverse=True)
        self.beginResetModel()
        for idx in indexes:
            del self._presets[idx]
        self.endResetModel()

    def load(self):
        self.beginResetModel()
        config = Config("filters_editor")
        presets = config.get("presets", {})
        self._presets = [
            (preset_name, filters) for preset_name, filters in presets.items()
        ]
        self.endResetModel()

    def save(self):
        config = Config("filters_editor", self.config_path)
        print(config._user_config)
        config["presets"] = {
            preset_name: filters for preset_name, filters in self._presets
        }
        config.save()

    def clear(self):
        self.beginResetModel()
        self._presets.clear()
        self.endResetModel()

    def preset_names(self):
        return [p[0] for p in self._presets]


class PresetButton(QToolButton):
    """A toolbutton that works with a drop down menu filled with a model"""

    preset_clicked = Signal(QAction)

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent=parent)
        self._menu = QMenu(self.tr("Presets"), self)
        self._menu.triggered.connect(self.preset_clicked)
        self.setPopupMode(QToolButton.InstantPopup)
        self._model: QAbstractItemModel = None
        self.setMenu(self._menu)
        self.setText(self.tr("Presets"))

    def set_model(self, model: QAbstractItemModel):
        self._model = model

    def mousePressEvent(self, e: QMouseEvent) -> None:
        if self._model:
            self._menu.clear()
            for i in range(self._model.rowCount()):
                index = self._model.index(i, 0)
                preset_name = index.data(Qt.DisplayRole)
                fields = index.data(Qt.UserRole)
                act: QAction = self._menu.addAction(preset_name)
                act.setData(fields)
        return super().mousePressEvent(e)


##------------END PRESETS


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
        values = get_field_unique_values_cached(
            self.conn, self.field_name, like, self.limit
        )
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
        null_action = self.line_edit.addAction(
            FIcon(0xF07E2), QLineEdit.TrailingPosition
        )
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
        null_action = self.line_edit.addAction(
            FIcon(0xF07E2), QLineEdit.TrailingPosition
        )
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

    def fill(self, operators=OPERATORS):
        """Init QComboBox with all supported operators"""
        self.combo_box.clear()
        for op in operators:
            self.combo_box.addItem(OPERATORS_PY_VQL.get(op), op)


class LogicFieldEditor(BaseFieldEditor):
    """Editor for logic field (And/Or)"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.box = QComboBox()

        # DisplayRole, UserRole
        self.box.addItem(OPERATORS_PY_VQL.get("$and"), "$and")
        self.box.addItem(OPERATORS_PY_VQL.get("$or"), "$or")

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


class FilterModel(QAbstractItemModel):
    """Model to display filter

    The model store Query filter as a nested tree of FilterItem.
    You can access data from self.item(), edit model using self.set_data()
    and helper methods like: add_logic_item, add_condition_item and remove_item.

    Attributes:
        conn (sqlite3.connection): sqlite3 connection
        root_item (FilterItem): RootItem (invisible) to store recursive item.

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
        model.load(data)
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

    def __init__(self, conn=None, parent=None):
        super().__init__(parent)
        self.root_item = FilterItem("$and")
        self.conn = conn
        self.clear()

        self.disable_font = QFont()
        self.disable_font.setStrikeOut(True)

    @property
    def filters(self):
        return self.to_dict()

    @filters.setter
    def filters(self, filters):
        self.load(filters)

    def __del__(self):
        """Model destructor."""
        del self.root_item

    def data(self, index: QModelIndex, role=Qt.EditRole):
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

            if index.column() == COLUMN_REMOVE:
                if index.parent() != QModelIndex():
                    return QIcon(FIcon(0xF0156, "red"))

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
                return QColor("lightgray")

        # align operator
        if role == Qt.TextAlignmentRole:
            if index.column() == COLUMN_OPERATOR:
                return Qt.AlignCenter

        # Role display or edit
        if role in (Qt.DisplayRole, Qt.EditRole):
            if index.column() == COLUMN_FIELD:
                if item.type == FilterItem.CONDITION_TYPE:
                    return item.get_field()

                if item.type == FilterItem.LOGIC_TYPE:
                    val = item.get_value()
                    return (
                        OPERATORS_PY_VQL.get(val, "$and") + f"  ({len(item.children)})"
                    )

            if item.type != FilterItem.CONDITION_TYPE:
                return

            if index.column() == COLUMN_OPERATOR:
                operator = item.get_operator()
                return OPERATORS_PY_VQL.get(operator, "=")

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

        if role == FilterModel.TypeRole:
            # Return item type
            return item.type

        if role == FilterModel.UniqueIdRole:
            return item.uuid

        return

        # if role == Qt.DisplayRole and index.column() == 1:
        #     data = self.item(index).get_data(index.column())
        #     return str(data)

        # if role in (Qt.DecorationRole, Qt.DisplayRole) and index.column() == 2:
        #     # Special case to display an icon instead of a number for gt fields
        #     field = self.item(index).get_data(0)
        #     if type(field) is tuple and field[2] == "gt":
        #         if role == Qt.DecorationRole:
        #             gt = self.item(index).get_data(index.column())
        #             return QIcon(GenotypeField.GENOTYPES[gt])
        #         else:
        #             # don't display any text
        #             return None
        # if role == Qt.DisplayRole or role == Qt.EditRole:
        #     #  Display data
        #     item = self.item(index)
        #     return item.get_data(index.column())

        # if role == Qt.TextAlignmentRole:
        #     #  Adjust text alignement
        #     if index.column() == 0:
        #         return int(Qt.AlignVCenter) + int(Qt.AlignLeft)
        #     if index.column() == 1:
        #         return Qt.AlignCenter
        #     if index.column() == 2:
        #         return int(Qt.AlignVCenter) + int(Qt.AlignLeft)

        # if role == Qt.FontRole:
        #     #  Make LogicItem as bold
        #     if self.item(index).type == FilterItem.LOGIC_TYPE:
        #         font = QFont()
        #         font.setBold(True)
        #         return font

    def setData(self, index, value, role=Qt.UserRole):
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

    def headerData(self, section, orientation, role=Qt.DisplayRole):
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
            parent_item = self.root_item

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

        if parent_item == self.root_item:
            return QModelIndex()

        return self.createIndex(parent_item.row(), 0, parent_item)

    def clear(self):
        """Clear Model"""
        self.beginResetModel()
        self.root_item.children.clear()
        # Load first default item
        self.root_item.append(FilterItem("$and"))

        self.endResetModel()

    def load(self, data: dict):
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
            self.root_item.children.clear()
            self.root_item.append(self.to_item(data))
        self.endResetModel()

    @classmethod
    def is_logic(cls, item: dict) -> bool:
        """
        Returns whether item holds a logic operator
        Example:
            > is_logic({"$and":[...]})
            > True
        """
        keys = list(item.keys())
        return keys[0] in ("$and", "$or")

    def to_item(self, data: dict) -> FilterItem:
        """Recursive function to build a nested FilterItem structure from dict data"""
        if FilterModel.is_logic(data):
            operator = list(data.keys())[0]
            item = FilterItem(operator)
            [item.append(self.to_item(k)) for k in data[operator]]
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

    def to_dict(
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

        if len(self.root_item.children) == 0:
            return {}

        if item is None:
            item = self.root_item[0]

        if checked_only:
            if item.type == FilterItem.LOGIC_TYPE and item.checked is True:
                # Return dict with operator as key and item as value
                operator_data = [
                    self.to_dict(child)
                    for child in item.children
                    if child.checked is True
                ]
                return {item.get_value(): operator_data}
        else:
            if item.type == FilterItem.LOGIC_TYPE:
                # Return dict with operator as key and item as value
                operator_data = [self.to_dict(child) for child in item.children]
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

    def remove_item(self, index):
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
            parent_item = self.root_item
        else:
            parent_item = parent.internalPointer()

        return len(parent_item.children)

    def columnCount(self, parent=QModelIndex()) -> int:
        """Overrided Qt methods: return column count according parent"""

        return 5

    def flags(self, index) -> Qt.ItemFlags:
        """Overrided Qt methods: return Qt flags to make item editable and selectable"""

        if not index.isValid():
            return 0

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
            return (
                Qt.ItemIsSelectable
                | Qt.ItemIsEditable
                | Qt.ItemIsEnabled
                | Qt.ItemIsDragEnabled
            )

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
            return self.root_item

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

        self.beginMoveRows(
            sourceParent, sourceRow, sourceRow, destinationParent, destinationChild
        )
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
            item_ = self.to_item(filter_dict)
        except Exception as e:
            # Invalid item
            return False
        if self.item(parent).type == FilterItem.LOGIC_TYPE:
            self.beginInsertRows(
                parent, self.rowCount(parent) - 1, self.rowCount(parent) - 1
            )
            self.item(parent).append(item_)
            self.endInsertRows()
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
            return True

        # Second case: row is valid. Only replace operator and value from condition, not
        index = parent.child(row, 0)
        if index.isValid():
            # When we drop a condition, we don't want to change the field. Only condition and value
            self.item(index).set_operator(condition.get("operator", "$eq"))
            self.item(index).set_value(condition.get("value", 7))
            self.dataChanged.emit(index, index)
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
            return self.moveRow(
                index.parent(), index.row(), destintation_parent, destination_row
            )
        return False

    def dropMimeData(
        self, data: QMimeData, action, row, column, parent: QModelIndex
    ) -> bool:
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

        data = QMimeData()
        parent = indexes[0]
        coords = []
        # Compute coords of index by recursively finding parent's row until root index.
        # First number in the list is the row among root parent children. Always 0, since there can be only one root as a logical operator
        while parent != QModelIndex():
            coords.insert(0, parent.row())
            parent = parent.parent()

        data = QMimeData()
        data.setData(
            "cutevariant/typed-json",
            bytes(json.dumps({"type": "internal_move", "coords": coords}), "utf-8"),
        )

        return data

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

        if data.hasText() and not data.hasUrls():
            obj = json.loads(data.text())
            if "type" in obj:
                if obj["type"] == "internal_move":
                    return True
            return True

        return True


class FilterDelegate(QStyledItemDelegate):
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

        s = qApp.style().pixelMetric(QStyle.PM_ListViewIconSize)
        self.icon_size = QSize(s, s)
        self.row_height = qApp.style().pixelMetric(QStyle.PM_ListViewIconSize) * 1.2

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
            level += 1

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
                if option.state & QStyle.State_Active
                or option.state & QStyle.State_Selected
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
                rect = QRect(
                    0, 0, option.decorationSize.width(), option.decorationSize.height()
                )
                rect.moveCenter(option.rect.center())
                # rect.setX(4)
                painter.drawPixmap(
                    rect.x(), rect.y(), decoration_icon.pixmap(option.decorationSize)
                )

        else:
            super().paint(painter, option, index)

        # Draw lines

        painter.setPen(QPen(QColor("lightgray")))
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


class FieldDialog(QDialog):
    # TODO: not used anymore
    def __init__(self, conn=None, parent=None):
        super().__init__(parent)
        self.title_label = QLabel("Non title")
        self.description_label = QLabel("Description")
        self.btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)

        self.field_box = QComboBox()
        self.field_operator = OperatorField()

        # setup combobox
        self.field_box.setEditable(True)
        # self.field_operator.setEditable(True)

        # setup label
        font = QFont()
        font.setBold(True)
        self.title_label.setFont(font)
        self.description_label.setWordWrap(True)

        v_layout = QVBoxLayout()
        v_layout.addWidget(self.title_label)
        v_layout.addWidget(self.description_label)
        v_layout.addSpacing(10)
        self.form_layout = QFormLayout()

        self.form_layout.addRow("Field", self.field_box)
        self.form_layout.addRow("Operator", self.field_operator)
        self.form_layout.addRow("Value", QSpinBox())

        v_layout.addLayout(self.form_layout)
        v_layout.addStretch(True)
        v_layout.addWidget(self.btn_box)

        self.setLayout(v_layout)

        self.setFixedSize(500, 300)

        self.field_box.currentIndexChanged.connect(self.on_field_changed)

        self.conn = conn

        self.btn_box.accepted.connect(self.accept)
        self.btn_box.rejected.connect(self.reject)

    @property
    def conn(self):
        return self._conn

    @conn.setter
    def conn(self, conn):
        self._conn = conn
        if self._conn:
            self.load_fields()

    def load_fields(self):
        """Load sql fields into combobox"""
        for field in sql.get_field_by_category(self.conn, "variants"):
            self.field_box.addItem(field["name"], field)

    def load_value_editor(self, sql_field):
        """Create a field widget according sql field name

        Args:
            sql_field (str): field name from sql field table
        """
        self.form_layout.removeRow(2)
        widget = FieldFactory(conn).create(sql_field)
        self.form_layout.addRow("value", widget)

    @Slot(int)
    def on_field_changed(self, index):
        """This method is triggered when a field has changed

        Args:
            index (int): current index from self.field_box
        """
        field = self.field_box.itemData(index)
        self.title_label.setText("{name} ({category})".format(**field))
        self.description_label.setText(field["description"])
        self.load_value_editor(field["name"])

    def get_condition(self):
        """Return current condition as a dictionnary

        Returns:
            Dictionnary exemple {"field":"chr", "operator":"=", value:5}

        """
        field = self.field_box.currentText()
        operator = self.field_operator.get_value()
        widget = self.form_layout.itemAt(5).widget()
        value = widget.get_value()

        return {"field": field, "operator": operator, "value": value}


class FiltersEditorWidget(plugin.PluginWidget):
    """Displayed widget plugin to allow creation/edition/deletion of filters"""

    ENABLE = True
    REFRESH_STATE_DATA = {"filters"}
    changed = Signal()

    def __init__(self, conn=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Filters")
        self.setWindowIcon(FIcon(0xF0232))

        self.settings = QSettings()
        self.view = QTreeView()

        # conn is always None here but initialized in on_open_project()
        self.model = FilterModel(conn)
        self.delegate = FilterDelegate()

        # Setup view
        self.view.setModel(self.model)
        self.view.setItemDelegate(self.delegate)
        self.view.setIndentation(10)
        self.view.setExpandsOnDoubleClick(False)
        self.view.setAlternatingRowColors(True)
        self.view.setAcceptDrops(True)
        self.view.setDragEnabled(True)
        self.view.setDragDropMode(QAbstractItemView.DragDrop)
        self.view.setAcceptDrops(True)
        # self.view.setDropIndicatorShown(True)
        self.view.header().setStretchLastSection(False)
        self.view.header().setSectionResizeMode(COLUMN_FIELD, QHeaderView.Interactive)
        self.view.header().setSectionResizeMode(COLUMN_OPERATOR, QHeaderView.Fixed)
        self.view.header().setSectionResizeMode(COLUMN_VALUE, QHeaderView.Stretch)
        self.view.header().setSectionResizeMode(
            COLUMN_CHECKBOX, QHeaderView.ResizeToContents
        )
        self.view.header().setSectionResizeMode(
            COLUMN_REMOVE, QHeaderView.ResizeToContents
        )
        self.view.setEditTriggers(QAbstractItemView.DoubleClicked)
        self.view.selectionModel().selectionChanged.connect(self.on_selection_changed)
        # self.view.header().hide()

        # Create toolbar
        self.toolbar = QToolBar()
        self.toolbar.setIconSize(QSize(16, 16))
        self.toolbar.setToolButtonStyle(Qt.ToolButtonIconOnly)

        self.add_condition_action = self.toolbar.addAction(
            FIcon(0xF0EF1), "Add condition", self.on_add_condition
        )
        self.add_condition_action.setToolTip("Add condition")
        self.add_group_action = self.toolbar.addAction(
            FIcon(0xF0EF0), "Add group", self.on_add_logic
        )
        self.add_group_action.setToolTip("Add Group")

        self.clear_all_action = self.toolbar.addAction(
            FIcon(0xF0234), self.tr("Clear all"), self.on_clear_all
        )

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.toolbar.addWidget(spacer)
        # Create preset combobox with actions
        self.toolbar.addSeparator()

        # Save button
        self.save_action = self.toolbar.addAction(self.tr("Save Preset"))
        self.save_action.setIcon(FIcon(0xF0818))
        self.save_action.triggered.connect(self.on_save_preset)
        self.save_action.setToolTip(self.tr("Save as a new Preset"))

        # Presets model
        self.presets_model = FiltersPresetModel(parent=self)

        self.presets_button = PresetButton(self)
        self.presets_button.set_model(self.presets_model)
        self.presets_button.preset_clicked.connect(self.on_select_preset)

        self.toolbar.addWidget(self.presets_button)

        # Presets toolbutton (with dropdown menu)
        self.update_presets()

        self.toolbar.addSeparator()

        apply_action = self.toolbar.addAction("Apply")
        self.apply_button = self.toolbar.widgetForAction(apply_action)
        self.apply_button.setText("Apply")
        self.apply_button.setIcon(FIcon(0xF0E1E, "white"))
        self.apply_button.setStyleSheet("background-color: #038F6A; color:white")
        self.apply_button.setAutoRaise(False)
        self.apply_button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.apply_button.triggered.connect(self.on_apply)
        main_layout = QVBoxLayout()

        main_layout.addWidget(self.toolbar)
        main_layout.addWidget(self.view)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(1)
        self.setLayout(main_layout)

        self.current_preset_name = ""

    @property
    def filters(self):
        return self.model.filters

    @filters.setter
    def filters(self, filters):
        self.model.filters = filters
        self.view.expandAll()

    def on_open_project(self, conn):
        """Overrided from PluginWidget"""
        self.model.conn = conn
        self.conn = conn

        # Clear lru_cache
        prepare_fields.cache_clear()
        get_field_unique_values_cached.cache_clear()
        self.on_refresh()

    def on_duplicate_filter(self):
        """Duplicate filter condition from context menu

        See contextMenu()
        """
        item_index = self.view.selectionModel().currentIndex()
        parent_index = item_index.parent()
        if not parent_index:
            return

        data = self.model.item(item_index).data
        self.model.add_condition_item(data, parent_index)

    def on_remove_filter(self):
        selected_index = self.view.selectionModel().currentIndex()
        if not selected_index:
            return

        # Safety, to avoid removing root item
        if not selected_index.parent().isValid():
            return

        confirmation = QMessageBox.question(
            self,
            self.tr("Please confirm"),
            self.tr(
                f"Do you really want to remove selected filter ? \nYou cannot undo this operation"
            ),
        )
        if confirmation == QMessageBox.Yes:
            self.model.remove_item(selected_index)

        # # The user deleted the preset that was selected last. So make it clear to the user that the preset doesn't exist anymore
        # if self.presets_button.text() not in action_names:
        #     self.presets_button.setText(self.tr("Select preset"))

        # self.presets_menu.addSeparator()

        # reset_act = QAction(self.tr("Clear"), self)
        # reset_act.triggered.connect(self.on_preset_clicked)

        # # When triggered, we will check for data and if None, we reset
        # reset_act.setData(None)
        # self.presets_menu.addAction(reset_act)
        # self.presets_menu.addAction(
        #     FIcon(0xF11E7), "Edit preset", self.on_edit_preset_pressed
        # )
        # self.presets_menu.addAction(FIcon(0xF0193), "Save", self.on_save_over_preset)
        # self.presets_menu.addAction(FIcon(0xF0415), "Save as new", self.on_save_preset)
        # self.presets_menu.addAction(FIcon(0xF054C), "Revert", self.on_revert_preset)

        # if selected_preset_action:
        #     selected_preset_action.trigger()

    def on_refresh(self):

        current_filters = self.mainwindow.get_state_data("filters")
        if self.filters == current_filters:
            # No change in filters = no refresh
            return

        self.model.clear()
        self.model.filters = current_filters

        self.refresh_buttons()
        self._update_view_geometry()

    def refresh_buttons(self):
        """Actualize the enable states of Add/Del buttons"""

        if self.filters:
            # Data

            # Add button: Is an item selected ?
            index = self.view.currentIndex()
            if index.isValid() and self.model.item(index).type == FilterItem.LOGIC_TYPE:
                self.add_condition_action.setEnabled(True)
                self.add_group_action.setEnabled(True)
            else:
                # item is CONDITION_TYPE or there is no item selected (because of deletion)
                self.add_condition_action.setEnabled(False)
                self.add_group_action.setEnabled(False)

    def on_apply(self):
        """Triggered when filters changed FROM THIS plugin

        Set the filters of the mainwindow and trigger a refresh of all plugins.
        """
        if self.mainwindow:

            # Close editor on validate, to avoid unset data
            self.close_current_editor()
            # Refresh other plugins only if the filters are modified
            self.mainwindow.set_state_data("filters", self.filters)
            self.mainwindow.refresh_plugins(sender=self)

        self.refresh_buttons()

    def close_current_editor(self):
        row = self.view.currentIndex().row()
        column = COLUMN_VALUE
        parent = self.view.currentIndex().parent()
        index = self.model.index(row, column, parent)

        widget = self.view.indexWidget(index)
        self.view.commitData(widget)
        self.view.closeEditor(
            widget,
            QAbstractItemDelegate.NoHint,
        )

    def on_add_logic(self):
        """Add logic item to the current selected index"""
        index = self.view.currentIndex()
        if index:
            self.model.add_logic_item(parent=index)
            # self.view.setFirstColumnSpanned(0, index.parent(), True)

            self._update_view_geometry()

    def to_json(self):
        """override"""

        return {"filters": self.filters}

    def from_json(self, data):
        """override"""
        if "filters" in data:
            self.filters = data["filters"]

    def update_presets(self):
        """Refresh self's preset model
        This method should be called by __init__ and on refresh
        """
        self.presets_model.load()

    def on_select_preset(self, action: QAction):
        """Activate when preset has changed from preset_combobox"""
        data = action.data()
        print("GERONIMOOOOOOO", data)
        if data:
            self.filters = action.data()
            self.on_apply()

    def on_save_preset(self):

        # So we don't accidentally save a preset that has not been applied yet...
        self.on_apply()

        name, ok = QInputDialog.getText(
            self,
            self.tr("Input dialog"),
            self.tr("Preset name:"),
            QLineEdit.Normal,
            QDir.home().dirName(),
        )
        i = 1
        while name in self.presets_model.preset_names():
            name = re.sub(r"\(\d+\)", "", name) + f" ({i})"
            i += 1

        if ok:
            self.mainwindow: MainWindow
            self.presets_model.add_preset(
                name, self.mainwindow.get_state_data("filters")
            )
            self.presets_model.save()

    def _update_view_geometry(self):
        """Set column Spanned to True for all Logic Item

        Allow Logic Item Editor to take all the space inside the row
        """
        self.view.expandAll()

        # self.view.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        # self.view.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)

        # for index in self.model.match(
        #     self.model.index(0, 0),
        #     FilterModel.TypeRole,
        #     FilterItem.LOGIC_TYPE,
        #     -1,
        #     Qt.MatchRecursive,
        # ):
        #     self.view.setFirstColumnSpanned(0, index.parent(), True)

    def on_add_condition(self):
        """Add new condition item

        - Add condition item to the current selected operator
        - Or add new operator and new condition item on a new filter
        """
        index = self.view.currentIndex()

        if index.isValid():
            if self.model.item(index).type == FilterItem.LOGIC_TYPE:
                # Add condition item to existing logic operator
                self.model.add_condition_item(parent=index)
        else:
            if self.model.rowCount() == 0:
                # Full new logic operator and condition item
                self.model.add_logic_item(parent=QModelIndex())
                gpindex = self.model.index(0, 0, QModelIndex())
                self.model.add_condition_item(parent=gpindex)

        self._update_view_geometry()
        self.refresh_buttons()

    def on_clear_all(self):
        """Clear all filters

        Ask user to be sure

        """

        ret = QMessageBox.question(
            self,
            self.tr("Remove all filters"),
            self.tr("Are you sure you want to remove all filters "),
        )

        if ret == QMessageBox.Yes:
            self.model.clear()

    def on_open_condition_dialog(self):
        """Open the condition creation dialog
        TODO: not used anymore
        """
        dialog = FieldDialog(conn=self.conn, parent=self)
        if dialog.exec_() == dialog.Accepted:
            cond = dialog.get_condition()
            index = self.view.currentIndex()
            if index:
                self.model.add_condition_item(parent=index, value=cond)

    def on_selection_changed(self):
        """Enable/Disable add button depending item type

        Notes:
            Disable Add button on CONDITION_TYPE
        """
        self.refresh_buttons()

    def remove_unchecked(self):
        """
        Remove unchecked filters from the filters tree model
        The trick here is that unchecked filters result in filters expression that has already
        been computed. So there is no need to compute it again.
        """
        self.model.filters = self.filters

    def contextMenuEvent(self, event: QContextMenuEvent):

        pos = self.view.viewport().mapFromGlobal(event.globalPos())
        index = self.view.indexAt(pos)

        if index.isValid():
            menu = QMenu(self)

            item = self.model.item(index)
            if item.type == FilterItem.LOGIC_TYPE:
                menu.addAction(self.add_condition_action)
                menu.addAction(self.add_group_action)

            # Check if this is not the root item
            if index.parent().isValid():
                menu.addAction(self.tr("Remove"), self.on_remove_filter)
                menu.addAction(self.tr("Duplicate"), self.on_duplicate_filter)

            menu.exec_(event.globalPos())

    def on_save_over_preset(self):

        settings = QSettings()
        preset_path = settings.value(
            "preset_path",
            QStandardPaths.writableLocation(QStandardPaths.GenericDataLocation),
        )
        preset_name = self.current_preset_name
        if os.path.isfile(f"{preset_path}/{preset_name}.filters.json"):
            with open(f"{preset_path}/{preset_name}.filters.json", "w") as file:
                obj = self.to_json()
                obj["name"] = preset_name
                json.dump(obj, file)

    def on_revert_preset(self):
        """
        Reverts the selected preset to its last saved version
        """
        settings = QSettings()
        preset_path = settings.value(
            "preset_path",
            QStandardPaths.writableLocation(QStandardPaths.GenericDataLocation),
        )
        preset_name = self.current_preset_name
        if os.path.isfile(f"{preset_path}/{preset_name}.filters.json"):
            with open(f"{preset_path}/{preset_name}.filters.json", "r") as file:
                obj = json.load(file)
                self.from_json(obj)


if __name__ == "__main__":

    app = QApplication(sys.argv)
    app.setStyle("fusion")

    style.dark(app)

    from cutevariant.core.importer import import_reader
    from cutevariant.core.reader import FakeReader
    import cutevariant.commons as cm
    from cutevariant.gui.ficon import FIcon, setFontPath

    setFontPath(cm.FONT_FILE)

    conn = sql.get_sql_connection(":memory:")
    import_reader(conn, FakeReader())

    data = {
        "$and": [
            {"chr": "chr12"},
            {"ref": "chr12"},
            {"ann.gene": "chr12"},
            {"ann.gene": "chr12"},
            {"pos": 21234},
            {"favorite": True},
            {"qual": {"$gte": 40}},
            {"ann.gene": {"$in": ["CFTR", "GJB2"]}},
            {"qual": {"$in": {"$wordset": "boby"}}},
            {"qual": {"$nin": {"$wordset": "boby"}}},
            {"samples.boby.gt": 1},
            {
                "$and": [
                    {"ann.gene": "chr12"},
                    {"ann.gene": "chr12"},
                    {"$or": [{"ann.gene": "chr12"}, {"ann.gene": "chr12"}]},
                ]
            },
        ]
    }

    # print(FilterModel.is_logic(data["$and"][6]))

    view = QTreeView()
    model = FilterModel()

    delegate = FilterDelegate()

    view.setModel(model)
    view.setItemDelegate(delegate)

    view.setModel(model)
    view.setAcceptDrops(True)
    view.setDragEnabled(True)
    view.setDropIndicatorShown(True)
    view.setSelectionBehavior(QAbstractItemView.SelectRows)
    view.setDragDropMode(QAbstractItemView.DragDrop)

    model.conn = conn
    model.load(data)

    view.expandAll()

    view.resize(800, 800)
    view.show()

    # view = QTreeView()
    # view.setEditTriggers(QAbstractItemView.DoubleClicked)
    # view.setAlternatingRowColors(True)
    # view.setUniformRowHeights(True)

    # view.setFirstColumnSpanned(0, QModelIndex(), True)
    # view.resize(500, 500)
    # view.show()
    # view.expandAll()

    app.exec_()
