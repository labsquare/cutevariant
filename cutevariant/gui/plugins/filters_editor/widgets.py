# Standard imports
import sys
import json
import os
import pickle
import uuid
from ast import literal_eval
from functools import lru_cache
from typing import Any, Iterable

# Qt imports
from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *

# Custom imports
from cutevariant.gui import style, plugin
from cutevariant.core import sql, get_sql_connection
from cutevariant.core.vql import parse_one_vql
from cutevariant.core.querybuilder import (
    build_vql_query,
    fields_to_vql,
    wordset_data_to_vql,
    WORDSET_FUNC_NAME,
)
import cutevariant.commons as cm

LOGGER = cm.logger()


@lru_cache()
def prepare_fields(conn):
    """Prepares a list of columns on which filters can be applied"""
    columns = []
    samples = [sample["name"] for sample in sql.get_samples(conn)]

    for field in sql.get_fields(conn):
        if field["category"] == "samples":
            # Replace the name for samples with:
            # ("sample", <individual_id>, <field_name>)
            # Ex: with a "name" equal to "ps":
            # {'id': 48, 'name': ('sample', 'HG001', 'ps'), 'category': 'samples',
            # 'type': 'str', 'description': ''}
            for sample in samples:
                temp_field = field.copy()
                temp_field["name"] = ("sample", sample, field["name"])
                columns.append(temp_field)
        else:
            columns.append(field)
    return columns


class BaseField(QFrame):
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

    def set_value(self, value):
        raise NotImplementedError

    def get_value(self):
        raise NotImplementedError

    def set_widget(self, widget):
        """Setup a layout with a widget

        Typically, it is used to add user input widget to the item
        (QSpinBox, QComboBox, etc.)

        Args:
            widget (QWidget)
        """
        self.widget = widget
        h_layout = QHBoxLayout()
        h_layout.addWidget(widget)
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setSpacing(0)
        self.setLayout(h_layout)


class IntegerField(BaseField):
    """Editor for integer value

    Attributes:
        spin_box (QSpinBox)
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.spin_box = QSpinBox()
        self.set_widget(self.spin_box)
        self.spin_box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def set_value(self, value: int):
        self.spin_box.setValue(value)

    def get_value(self) -> int:
        return self.spin_box.value()

    def set_range(self, min_, max_):
        """ Limit editor with a range of value """
        self.spin_box.setRange(min_, max_)


class FloatField(BaseField):
    """Editor for floating point value

    Attributes:
        spin_box (QDoubleSpinBox)
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.spin_box = QDoubleSpinBox()
        self.set_widget(self.spin_box)
        self.spin_box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def set_value(self, value: int):
        self.spin_box.setValue(value)

    def get_value(self) -> float:
        return self.spin_box.value()

    def set_range(self, min_, max_):
        self.spin_box.setRange(min_, max_)


class StrField(BaseField):
    """Editor for string value

    Attributes:
        edit (QLineEdit)
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.edit = QLineEdit()
        self.edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.set_widget(self.edit)

    def set_value(self, value: Any):
        """Set displayed value in the lineEdit of the editor

        Notes: TODO: TO be updated/removed if WORDSET is a real operator
            For the following query:
            SELECT favorite,chr,pos,ref,alt FROM variants where gene IN WORDSET['aa']

            We need to show to the user only "WORDSET['aa']"; not the internal
            representation: ("WORDSET", "aa"). This must be done in
            the model that return one representation or the other according to
            DisplayRole or UserRole.

            Here we get the internal representation (tuple) from the UserRole
            of the model.
            So we need to cast it via wordset_data_to_vql().

            The opposite is made in get_value() that MUST return internal
            representation.
        """
        # TODO: ugly cast to handle tuple corresponding to (WORDSET, name)
        if isinstance(value, tuple) and value[0] == WORDSET_FUNC_NAME:
            value = wordset_data_to_vql(value)

        self.edit.setText(str(value))

    def get_value(self) -> Any:
        """Return string or float/int for numeric values"""
        value = self.edit.text()

        # TODO: ugly cast to return tuple corresponding to (WORDSET, name)
        # Please just leave pass in this section if WORDSET is converted to normal operator
        import re
        match = re.search(r"WORDSET\[['\"](.*)['\"]\]", value)
        if match:
            return "WORDSET", match[1]

        if value.isdigit():
            return int(value)

        if value.isdecimal():
            return float(value)
        return value

    def set_completer(self, completer: QCompleter):
        """Set a completer to autocomplete value"""
        self.edit.setCompleter(completer)


class IterableField(StrField):
    """Editor for iterables in string form.

    Attributes:
        edit (QLineEdit)
    """

    def set_value(self, value: Iterable):
        """Set displayed value in the lineEdit of the editor"""
        print("Iterable field set value ?", value, type(value))
        super().set_value(value)

    def get_value(self) -> tuple:
        """Return the value of the field in tuple type

        Notes:
            Try to cast the follwing terms into tuples:
            - 'a, b' => ('a', 'b')
            - 'a,b' => ...
            - '(a, b' => ...
            - 'a,b)" => ...
            - ('a', 'b') => ...
            - (1, 2) => (1, 2)

        Returns:
            (tuple): Casted from string
        """
        value = self.edit.text()

        try:
            if "," in value and ("(" not in value or ")" not in value):
                value = value.replace("(", "").replace(")", "").replace(", ", ",")
                value = tuple(value.split(","))
                # print("splitted value", value)
                return value

            # Cast proper tuple
            return literal_eval(value)
        except ValueError:
            pass
        # Cast to str
        return super().get_value()


class ComboField(BaseField):
    """Editor for string value

    Notes:
        Items are added in FilterDelegate.createEditor()

    Attributes:
        edit (QLineEdit)
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.edit = QComboBox()
        self.edit.setEditable(True)
        self.edit.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.set_widget(self.edit)

    def set_value(self, value: str):
        """Set text of lineEdit in ComboBox"""
        # items = [self.edit.itemText(i) for i in range(self.edit.count())]
        # Set text of lineEdit via the index of the required text
        # Here we use an editable combobox with a lineEdit.
        # => Use setCurrentIndex instead of setCurrentText.
        # The last one doesn't refresh the index and thus the currentData.
        # In this case, get_value will return the currentData of the first item
        # in ComboBox regardless the item in the lineEdit.
        index = self.edit.findText(value)
        if index != -1:
            self.edit.setCurrentIndex(index)
            # /!\ Don't do this only: self.edit.setCurrentText(value) (see above)

    def get_value(self):
        """Return UserRole string"""
        # Return UserRole
        return self.edit.currentData()

    def addItems(self, words: list):
        """Set a completer to autocomplete value"""
        self.edit.clear()
        self.edit.addItems(words)


class BoolField(BaseField):
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


class OperatorField(BaseField):
    """Editor for Logic Value (less, greater, more than etc ...)

    Attributes:
        combo_box (QComboBox): Combobox to allow a suer to select operators.
    """

    # Symbols used in VQL vs text descriptions
    SYMBOLS = {
        "<": "less",
        "<=": "less or equal",
        ">": "greater",
        ">=": "greater or equal",
        "=": "equal",
        "!=": "not equal",
        "LIKE": "like",
        "NOT LIKE": "not like",
        "~": "regex",
        "IN": "in",
        "NOT IN": "not in",
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.combo_box = QComboBox()
        self.set_widget(self.combo_box)
        self.combo_box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self._fill()

    def set_value(self, value: str):
        assert value.upper() in self.SYMBOLS
        self.combo_box.setCurrentText(self.SYMBOLS[value.upper()])

    def get_value(self) -> str:
        # Return UserRole
        return self.combo_box.currentData()

    def _fill(self):
        """Init QComboBox with all supported operators"""
        self.combo_box.clear()
        for symbol, text in self.SYMBOLS.items():
            # DisplayRole, UserRole
            self.combo_box.addItem(text, symbol)


class LogicField(BaseField):
    """Editor for logic field (And/Or)"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.box = QComboBox()

        # DisplayRole, UserRole
        self.box.addItem("AND", "AND")
        self.box.addItem("OR", "OR")

        self.box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.set_widget(self.box)

    def set_value(self, value: str):

        if value.upper() == "OR":
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

        self.field_types_mapping = {
            field["name"]: field["type"] for field in prepare_fields(conn)
        }

    def create(self, sql_field, parent=None):
        """Get FieldWidget according to type key of the given sql_field"""
        # sample fields are stored as tuples
        # if type(sql_field) is tuple:
        # sample = sql_field[1]
        # sql_field = sql_field[2]
        # else:
        # # Passing sample has no effect for non-sample fields
        # sample = None

        # Get field data by its name in DB
        # Don't work anymore because some fields (samples related)
        # have a tuple structure.
        # See prepare_fields()
        # field_type = sql.get_field_by_name(self.conn, sql_field)

        field_type = self.field_types_mapping.get(sql_field)
        assert field_type

        if field_type == "int":
            w = IntegerField(parent)
            # w.set_range(*sql.get_field_range(self.conn, sql_field, sample))
            return w

        if field_type == "float":
            w = FloatField(parent)
            # w.set_range(*sql.get_field_range(self.conn, sql_field, sample))
            return w

        if field_type == "str":
            return StrField(parent)

        if field_type == "bool":
            return BoolField(parent)

        return StrField(parent)


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
            return self.data[1].upper()

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
            self.data[1] = value.upper()

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
        data = {"AND": [
        {"field": "ref", "operator": "=", "value": "A"},
        {
            "OR": [
                {"field": "chr", "operator": "=", "value": "chr5"},
                {"field": "chr", "operator": "=", "value": "chr3"},
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
    _HEADERS = ["c", "field", "operator", "value", "op"]
    _MIMEDATA = "application/x-qabstractitemmodeldatalist"

    # Custom type to get FilterItem.type. See self.data()
    TypeRole = Qt.UserRole + 1
    UniqueIdRole = Qt.UserRole + 2

    filtersChanged = Signal()

    def __init__(self, conn=None, parent=None):
        super().__init__(parent)
        self.root_item = FilterItem("AND")
        self.conn = conn

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

        item = self.item(index)

        if role in (Qt.DisplayRole, Qt.EditRole, Qt.UserRole):
            if index.column() == 0:
                return item.checked if role == Qt.UserRole else str(item.checked)

            if index.column() == 1:
                if item.type == FilterItem.CONDITION_TYPE:
                    return fields_to_vql(item.get_field())

                if item.type == FilterItem.LOGIC_TYPE:
                    val = item.get_value()
                    return val if role == Qt.UserRole else str(val)

            if item.type != FilterItem.CONDITION_TYPE:
                return

            if index.column() == 2:
                operator = item.get_operator()
                return operator if role == Qt.UserRole else str(operator)

            if index.column() == 3:
                val = item.get_value()
                # TODO: WORDSET handling here. To be modified if WORDSET is a real operator
                # Same way that for fields formatting in VQL form for column 1
                if (
                    role in (Qt.EditRole, Qt.DisplayRole)
                    and isinstance(val, tuple)
                    and val[0] == WORDSET_FUNC_NAME
                ):
                    return wordset_data_to_vql(val)

                return val if role == Qt.UserRole else str(val)

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

            if index.column() == 0:
                item.checked = bool(value)

            if index.column() == 1:
                if item.type == FilterItem.LOGIC_TYPE:
                    item.set_value(value)

                if item.type == FilterItem.CONDITION_TYPE:
                    item.set_field(value)

            if item.type == FilterItem.CONDITION_TYPE:

                if index.column() == 2:
                    item.set_operator(value)

                if index.column() == 3:
                    item.set_value(value)

            self.filtersChanged.emit()
            # just one item is changed
            self.dataChanged.emit(index, index, role)
            return True

        if role == Qt.CheckStateRole:
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
        """Overrided Qt methods: Create parent from index """
        if not index.isValid():
            return QModelIndex()

        child_item = index.internalPointer()
        parent_item = child_item.parent

        if parent_item == self.root_item:
            return QModelIndex()

        return self.createIndex(parent_item.row(), 0, parent_item)

    def clear(self):
        """Clear Model"""
        self.root_item.children.clear()

    def load(self, data: dict):
        """load model from dict

        dict should be a nested dictionnary of condition. For example:
        data = {"AND": [
        {"field": "ref", "operator": "=", "value": "A"},
        {
            "OR": [
                {"field": "chr", "operator": "=", "value": "chr5"},
                {"field": "chr", "operator": "=", "value": "chr3"},
            ]
        },}}
        Args:
            data (TYPE): Description
        """
        self.beginResetModel()
        self.clear()
        if data:
            self.root_item.append(self.to_item(data))
        self.endResetModel()

    def to_item(self, data: dict) -> FilterItem:
        """Recursive function to build a nested FilterItem structure from dict data"""
        if len(data) == 1:  # logic item
            operator = list(data.keys())[0]
            item = FilterItem(operator)
            [item.append(self.to_item(k)) for k in data[operator]]
        else:  # condition item
            item = FilterItem((data["field"], data["operator"], data["value"]))
        return item

    def to_dict(self, item=None) -> dict:
        """Recursive function to build a nested dictionnary from FilterItem structure

        Notes:
            We use data from FilterItems; i.e. the equivalent of UserRole data.
        """

        if len(self.root_item.children) == 0:
            return {}

        if item is None:
            item = self.root_item[0]

        if item.type == FilterItem.LOGIC_TYPE and item.checked is True:
            # Return dict with operator as key and item as value
            operator_data = [
                self.to_dict(child) for child in item.children if child.checked is True
            ]
            return {item.get_value(): operator_data}

        if item.type == FilterItem.CONDITION_TYPE:
            return {
                "field": item.get_field(),
                "operator": item.get_operator(),
                "value": item.get_value(),
            }

    def add_logic_item(self, value="AND", parent=QModelIndex()):
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

    def add_condition_item(self, value=("chr", ">", "100"), parent=QModelIndex()):
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
        """Overrided Qt methods: return row count according parent """
        if parent.column() > 0:
            return 0

        if not parent.isValid():
            parent_item = self.root_item
        else:
            parent_item = parent.internalPointer()

        return len(parent_item.children)

    def columnCount(self, parent=QModelIndex()) -> int:
        """ Overrided Qt methods: return column count according parent """

        return 5

    def flags(self, index) -> Qt.ItemFlags:
        """ Overrided Qt methods: return Qt flags to make item editable and selectable """

        if not index.isValid():
            return 0

        item = index.internalPointer()

        if index.column() == 0 or index.column() == 4:
            return Qt.ItemIsSelectable | Qt.ItemIsEnabled

        if item.type == FilterItem.LOGIC_TYPE and index.column() != 1:
            return Qt.ItemIsSelectable | Qt.ItemIsEnabled

        if item.type == FilterItem.LOGIC_TYPE and index.column() == 1:
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

        #  if destination is - 1, it's mean we should append the item at the end of children
        if destinationChild < 0:
            if sourceParent == destinationParent:
                return False
            else:
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
        return Qt.MoveAction

    def dropMimeData(self, data, action, row, column, parent) -> bool:
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
        if action != Qt.MoveAction:
            return False

        if not data.data(self._MIMEDATA):
            return False

        # Unserialize
        item = pickle.loads(data.data(self._MIMEDATA).data())

        # Get index from item
        source_parent = self.match(
            self.index(0, 0),
            FilterModel.UniqueIdRole,
            item.parent.uuid,
            1,
            Qt.MatchRecursive,
        )

        if source_parent:
            source_parent = source_parent[0]
            return self.moveRow(source_parent, item.row(), parent, row)

        return False

    def mimeData(self, indexes) -> QMimeData:
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

        data = QMimeData(self._MIMEDATA)
        serialization = QByteArray(pickle.dumps(self.item(indexes[0])))
        data.setData(self._MIMEDATA, serialization)
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

    COLUMN_CHECKBOX = 0
    COLUMN_FIELD = 1
    COLUMN_LOGIC = 1
    COLUMN_OPERATOR = 2
    COLUMN_VALUE = 3
    COLUMN_REMOVE = 4

    def __init__(self, parent=None):
        super().__init__(parent)

        self.add_icon = FIcon(0xF0419)
        self.rem_icon = FIcon(0xF0156)

        self.eye_on = FIcon(0xF06D0)
        self.eye_off = FIcon(0xF06D1)

        self.icon_size = QSize(16, 16)

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
        # Get current sql connection
        conn = model.conn

        if index.column() == 1:
            if item.type == FilterItem.LOGIC_TYPE:
                # AND/OR logic operators
                return LogicField(parent)

            if item.type == FilterItem.CONDITION_TYPE:
                # Display all fields of the database
                widget = ComboField(parent)
                # LOGGER.debug(prepare_fields.cache_info())
                # Add items
                for field in prepare_fields(conn):
                    # Cast ('sample', 'HG001', 'gt') to sample['HG001'].gt
                    # Leave "chr" to "chr"
                    text = fields_to_vql(field["name"])
                    widget.edit.addItem(text, field["name"])

                return widget

        if index.column() == 2:
            return OperatorField(parent)

        if index.column() == 3:
            if model.item(index).get_operator() in ("IN", "NOT IN"):
                # Tuple value is expecitem required
                return IterableField(parent)
            # Basic string or int or float
            return StrField(parent)
            # Dynamic field according to database type
            # return FieldFactory(conn).create(model.item(index).get_field(), parent=parent)

        return super().createEditor(parent, option, index)

    def setEditorData(self, editor: QWidget, index: QModelIndex):
        """Overrided from Qt: Read data from model (FilterItem) and set editor data

        TL;DR: populate the editor with the data from the model.

        Sets the contents of the given editor, with the data of the item at the
        given index.

        Currently, it calls BaseEditor.set_value() methods

        See Also:
            :meth:`setModelData` for the opposite function (set model data)

        Args:
            editor (QWidget)
            index (QModelindex)
        """
        # print("SET editor val from model:")
        # roles = (Qt.UserRole, Qt.EditRole, Qt.DisplayRole)
        # print("user, edit, display")
        # print(";".join(str(index.data(role)) for role in roles))
        # print(";".join(str(type(index.data(role))) for role in roles))
        # print("VAL:", index.data(role=Qt.UserRole))
        # print("editor type", type(editor))

        # Set editor data from the model (from the selected FilterItem)
        # Editors expect typed values, so don't forget to use UserRole, not EditRole
        editor.set_value(index.data(role=Qt.UserRole))

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

        if event.type() == QEvent.MouseButtonPress:
            # print("mouse pressed on", index.column(), event.button())
            item = model.item(index)

            if index.column() == self.COLUMN_CHECKBOX and self._check_rect(
                option.rect
            ).contains(event.pos()):
                # Invert check state
                model.setData(index, not item.checked, role=Qt.CheckStateRole)
                return True

            if index.column() == self.COLUMN_REMOVE and self._check_rect(
                option.rect
            ).contains(event.pos()):
                # Remove item
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
        # val = editor.get_value()
        # print("SET data model from editor:", val, type(val))
        # Get typed data from the editor (i.e. not a string)
        # Then set this data to the FilterItem (in the corresponding attribute)
        # via its set_value() function.
        # Default: UserRole
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

        size = QSize(option.rect.width(), 30)

        if index.column() == self.COLUMN_CHECKBOX:
            return QSize(20, 30)

        if index.column() == self.COLUMN_OPERATOR:
            return QSize(20, 30)

        if index.column() == self.COLUMN_FIELD:
            margin = self._compute_margin(index)
            size.setWidth(size.width() + margin + 10)

        return size

    def _compute_level(self, index: QModelIndex):
        level = 0
        i = index.parent()
        while i.isValid():
            i = i.parent()
            level += 1

        return level

    def _compute_margin(self, index: QModelIndex):
        return self._compute_level(index) * 10 + 5

    def paint(
        self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex
    ):

        item = index.model().item(index)
        is_selected = False

        if option.state & QStyle.State_Enabled:
            bg = (
                QPalette.Normal
                if option.state & QStyle.State_Active
                else QPalette.Inactive
            )
        else:
            bg = QPalette.Disabled

        if option.state & QStyle.State_Selected:
            is_selected = True
            painter.fillRect(option.rect, option.palette.color(bg, QPalette.Highlight))

        # Indentation level
        margin = self._compute_margin(index)

        rect = option.rect
        # Add margin for column 1 and 0
        if index.column() <= 1:
            rect.setLeft(rect.x() + margin)

        # ========== Check box ====================
        if index.column() == self.COLUMN_CHECKBOX:
            # cbOpt = QStyleOptionButton()
            # cbOpt.rect = self._check_rect(rect)
            # cbOpt.setLeft(cbOpt.rect.x() + margin)
            # cbOpt.state |= QStyle.State_On if item.checked else QStyle.State_Off
            # QApplication.instance().style().drawControl(QStyle.CE_CheckBox, cbOpt, painter)

            check_icon = self.eye_on if item.checked else self.eye_off
            rect = QRect(0, 0, self.icon_size.width(), self.icon_size.height())
            rect.moveCenter(option.rect.center())
            rect.setX(4)
            painter.drawPixmap(rect.x(), rect.y(), check_icon.pixmap(self.icon_size))

        if index.column() > self.COLUMN_CHECKBOX:

            font = QFont()
            align = Qt.AlignVCenter
            color = option.palette.color(
                QPalette.Normal if item.checked else QPalette.Disabled,
                QPalette.HighlightedText if is_selected else QPalette.WindowText,
            )

            if item.type == FilterItem.LOGIC_TYPE:
                font.setBold(True)

            if index.column() == self.COLUMN_FIELD:
                align |= Qt.AlignLeft

            if index.column() == self.COLUMN_OPERATOR:
                align |= Qt.AlignCenter

            if index.column() == self.COLUMN_VALUE:
                align |= Qt.AlignLeft

            painter.setFont(font)
            painter.setPen(color)
            painter.drawText(rect, align, index.data(Qt.DisplayRole))

            if index.column() == self.COLUMN_REMOVE:
                rect = QRect(0, 0, self.icon_size.width(), self.icon_size.height())
                rect.moveCenter(option.rect.center())
                painter.drawPixmap(
                    rect.right() - self.icon_size.width(),
                    rect.y(),
                    self.rem_icon.pixmap(self.icon_size),
                )

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

        if index.column() == 1:
            margin = self._compute_margin(index)
            option.rect.setLeft(option.rect.x() + margin)
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
    changed = Signal()

    def __init__(self, conn=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Filters"))

        self.settings = QSettings()
        self.view = QTreeView()
        # conn is always None here but initialized in on_open_project()
        self.model = FilterModel(conn)
        self.delegate = FilterDelegate()
        self.toolbar = QToolBar()
        self.toolbar.setIconSize(QSize(16, 16))

        # Drag & drop
        self.view.setModel(self.model)
        self.view.setItemDelegate(self.delegate)
        self.view.setDragEnabled(True)
        self.view.header().setStretchLastSection(False)
        self.view.setAcceptDrops(True)
        self.view.setDragDropMode(QAbstractItemView.InternalMove)
        self.view.setAlternatingRowColors(True)
        self.view.setIndentation(0)

        self.view.header().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.view.header().setSectionResizeMode(1, QHeaderView.Stretch)
        self.view.header().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.view.header().setSectionResizeMode(3, QHeaderView.Stretch)
        self.view.header().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.view.setEditTriggers(
            QAbstractItemView.CurrentChanged  # whenever current item changes.
            | QAbstractItemView.SelectedClicked  # when clicking on an already selected item (slow)
            | QAbstractItemView.DoubleClicked  # item is double clicked.
        )
        # Item selected in view
        self.view.selectionModel().selectionChanged.connect(self.on_selection_changed)
        self.view.header().hide()

        self.combo = QComboBox()
        self.combo.addItem(self.tr("Current not saved filter..."))
        self.combo.currentTextChanged.connect(self.on_combo_changed)
        self.load_predefined_filters()

        self.save_button = QToolButton()
        self.save_button.setIcon(FIcon(0xF0193))
        self.save_button.setToolTip(self.tr("Save the current filter"))
        self.save_button.clicked.connect(self.on_save_filters)
        self.del_button = QToolButton()
        self.del_button.setDefaultAction(
            QAction(FIcon(0xF0A7A), self.tr("Delete the filter"))
        )
        self.del_button.clicked.connect(self.on_delete_item)
        # Adjust heights
        # self.combo.setMinimumHeight(30)
        # self.save_button.setMinimumHeight(30)
        # self.del_button.setMinimumHeight(30)

        hlayout = QHBoxLayout()
        hlayout.addWidget(self.combo)
        hlayout.addWidget(self.save_button)
        hlayout.addWidget(self.del_button)

        layout = QVBoxLayout()
        layout.addLayout(hlayout)
        layout.addWidget(self.view)
        layout.addWidget(self.toolbar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(1)
        self.setLayout(layout)

        # setup Menu
        self.add_button = self.toolbar.addAction(
            FIcon(0xF0415), self.tr("Add Condition"), self.on_add_condition
        )
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.model.filtersChanged.connect(self.on_filters_changed)

    @property
    def filters(self):
        return self.model.filters

    @filters.setter
    def filters(self, filters):
        self.model.filters = filters

    def on_open_project(self, conn):
        """Overrided from PluginWidget"""
        self.model.conn = conn
        self.conn = conn

        # Clear lru_cache
        prepare_fields.cache_clear()

        self.on_refresh()

    def load_predefined_filters(self):
        """Load user and software defined filters)

        - Software defined filters are loaded from "filter.json" embedded
            in the current plugin folder.
        - User defined filters are loaded from app settings, under the key
            `plugins/filters_editor/filters`.
        """
        json_file_path = os.path.join(os.path.dirname(__file__), "filters.json")

        filters = dict()
        # Open from embedded JSON and load software filters
        if os.path.isfile(json_file_path):
            with open(json_file_path, encoding="utf8") as f_d:
                try:
                    filters = json.loads(f_d.read())
                except json.decoder.JSONDecodeError as e:
                    LOGGER.exception(e)
            LOGGER.debug("Loaded predefined filters:", filters)

        # Overwrite software filters with user defined filters
        self.settings.beginGroup("plugins/filters_editor/filters")
        filters.update(
            {
                filter_name: self.settings.value(filter_name)
                for filter_name in self.settings.childKeys()
            }
        )
        self.settings.endGroup()

        # Load in combobox
        for filter_name, filter_query in filters.items():
            vql_obj = parse_one_vql(filter_query)
            self.combo.addItem(filter_name, vql_obj["filters"])

    def on_refresh(self):
        """Overrided"""
        if self.filters == self.mainwindow.state.filters:
            # No change in filters = no refresh
            return

        # Filters changed: Update UserRole of default filter and select it
        self.combo.setItemData(0, self.mainwindow.state.filters)
        self.combo.setCurrentIndex(0)

        self.refresh_buttons()
        self._update_view_geometry()

    def refresh_buttons(self):
        """Actualize the enable states of Add/Del buttons"""
        if self.filters:
            # Data
            # Deletion/clear is always possible
            self.del_button.setEnabled(True)

            # Add button: Is an item selected ?
            index = self.view.currentIndex()
            if index.isValid() and self.model.item(index).type == FilterItem.LOGIC_TYPE:
                self.add_button.setEnabled(True)
            else:
                # item is CONDITION_TYPE or there is no item selected (because of deletion)
                self.add_button.setEnabled(False)
        else:
            # Empty
            self.add_button.setEnabled(True)

            current_index = self.combo.currentIndex()
            if current_index == 0:
                # Not saved filter => useless to delete it
                self.del_button.setEnabled(False)
            else:
                # Saved filter => allow its deletion
                self.del_button.setEnabled(True)

    def on_filters_changed(self):
        """Triggered when filters changed FROM THIS plugin

        Set the filters of the mainwindow and trigger a refresh of all plugins.
        """
        if self.mainwindow and self.filters != self.mainwindow.state.filters:
            # Refresh other plugins only if the filters are modified
            self.mainwindow.state.filters = self.filters
            self.mainwindow.refresh_plugins(sender=self)

        # Filters changed:
        # - item in combobox has been changed
        # - filters in current filter has been changed
        # Filters are read only, so we must go to the unsaved one.
        current_index = self.combo.currentIndex()
        if current_index != 0 and self.combo.currentData() != self.filters:
            # Update UserRole of default no saved filter and select it
            self.combo.blockSignals(True)
            self.combo.setItemData(0, self.filters)
            self.combo.setCurrentIndex(0)
            self.combo.blockSignals(False)

        self.refresh_buttons()

    def on_add_logic(self):
        """Add logic item to the current selected index"""
        index = self.view.currentIndex()
        if index:
            self.model.add_logic_item(parent=index)
            # self.view.setFirstColumnSpanned(0, index.parent(), True)

            self._update_view_geometry()

    def on_save_filters(self):
        """Called when Save button is clicked

        Save the current filter into a new independent filter:
            - In the combobox
            - In user defined filters (in app settings, under the key
                `plugins/filters_editor/filters`);
                Note that such filters are removed when a user clicks on
                del_button.
        """
        filter_name, _ = QInputDialog.getText(
            self, self.tr("Type a name for the filter"), self.tr("Filter Name:")
        )
        if not filter_name:
            return

        # Save current filters in UserRole of a new ComboBox item
        self.combo.addItem(filter_name, self.filters)
        self.combo.setCurrentIndex(self.combo.findText(filter_name))

        # Convert current query into VQL query and save it in app settings
        vql_query = build_vql_query(
            self.mainwindow.state.fields,
            self.mainwindow.state.source,
            self.mainwindow.state.filters,
            self.mainwindow.state.group_by,
            self.mainwindow.state.having,
        )

        self.settings.beginGroup("plugins/filters_editor/filters")
        self.settings.setValue(filter_name, vql_query)
        self.settings.endGroup()

    def on_combo_changed(self):
        """Called when a new item is selected in the ComboBox (programatically or not)"""
        filters = self.combo.currentData()
        if filters:
            self.filters = filters
        else:
            # Empty filter
            self.model.clear()

        self._update_view_geometry()
        self.on_filters_changed()

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

    def on_delete_item(self):
        """Delete current item

        - if filter is saved => delete filter
        - if filter is not saved => clear
        """
        ret = QMessageBox.question(
            self,
            self.tr("Filter deletion"),
            self.tr("Do you want to remove this filter?"),
            QMessageBox.Yes | QMessageBox.No,
        )

        if ret == QMessageBox.Yes:
            current_index = self.combo.currentIndex()
            if current_index == 0:
                # Not saved filter
                self.model.clear()
            else:
                # Saved filter
                # Delete from app settings
                self.settings.beginGroup("plugins/filters_editor/filters")
                self.settings.remove(self.combo.currentText())
                self.settings.endGroup()

                # Delete from combobox
                self.combo.removeItem(current_index)

            self.refresh_buttons()

    def on_selection_changed(self):
        """Enable/Disable add button depending item type

        Notes:
            Disable Add button on CONDITION_TYPE
        """
        self.refresh_buttons()

    def contextMenuEvent(self, event: QContextMenuEvent):

        pos = self.view.viewport().mapFromGlobal(event.globalPos())
        index = self.view.indexAt(pos)

        if index.isValid():
            menu = QMenu(self)

            item = self.model.item(index)
            if item.type == FilterItem.LOGIC_TYPE:
                menu.addAction(self.tr("Add condition"), self.on_add_condition)
                menu.addAction(self.tr("Add subfilter"), self.on_add_logic)

            menu.exec_(event.globalPos())


if __name__ == "__main__":

    app = QApplication(sys.argv)
    app.setStyle("fusion")

    style.dark(app)

    from cutevariant.core.importer import import_reader
    from cutevariant.core.reader import FakeReader
    import cutevariant.commons as cm
    from cutevariant.gui.ficon import FIcon, setFontPath

    conn = get_sql_connection("test.db")

    d = FieldDialog(conn)
    d.show()
    # ---

    setFontPath(cm.FONT_FILE)

    conn = sql.get_sql_connection(":memory:")
    import_reader(conn, FakeReader())

    data = {
        "AND": [
            {"field": "gene", "operator": "=", "value": "chr12"},
            {"field": "gene", "operator": "=", "value": "chr12"},
            {"field": "gene", "operator": "=", "value": "chr12"},
            {"field": "gene", "operator": "=", "value": "chr12"},
            {"field": "gene", "operator": "=", "value": "chr12"},
            {"field": "gene", "operator": "=", "value": "chr12"},
        ]
    }

    view = FiltersEditorWidget()
    view.model.conn = conn
    view.model.load(data)

    view._update_view_geometry()
    view.show()

    # view = QTreeView()
    # view.setEditTriggers(QAbstractItemView.DoubleClicked)
    # view.setAlternatingRowColors(True)
    # view.setUniformRowHeights(True)
    # view.setModel(model)
    # view.setAcceptDrops(True)
    # view.setDragEnabled(True)
    # view.setDropIndicatorShown(True)
    # view.setSelectionBehavior(QAbstractItemView.SelectRows)
    # view.setDragDropMode(QAbstractItemView.InternalMove)

    # view.setFirstColumnSpanned(0, QModelIndex(), True)
    # view.resize(500, 500)
    # view.show()
    # view.expandAll()

    app.exec_()
