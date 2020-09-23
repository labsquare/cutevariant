from cutevariant.gui.ficon import FIcon
from cutevariant.gui.fields import *

from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *
import sys
from cutevariant.gui import style, plugin
import pickle
import uuid

# Some fields editors

from cutevariant.core import sql, get_sql_connexion


def prepare_fields(conn):
    """Prepares a list of columns on which filters can be applied
    """
    columns = []
    samples = [s["name"] for s in sql.get_samples(conn)]
    for field in sql.get_fields(conn):
        if field["category"] == "samples":
            for sample in samples:
                field["name"] = "samples['{}'].{}".format(sample, field["name"])
                columns.append(field)
        else:
            columns.append(field)
    return columns


class BaseField(QFrame):
    """Base class for all editor widgets. Editor widgets are used in FilterDelegate to display different kind of editor according field type.
    Inherit from this class if you want a custom field editor by overriding  set_value and get_value.
        ..note: I don't want to use @property for value. It doesn't suitable for POO in my point of view
        ..see: FilterDelegate
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

    def get_value(self) -> int:
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

    def set_value(self, value: str):
        self.edit.setText(str(value))

    def get_value(self):
        """Return quoted string
            ..todo : check if quotes are required
        """
        value = self.edit.text()

        if value.isdigit():
            return int(value)

        if value.isdecimal():
            return float(value)

        return value

    def set_completer(self, completer: QCompleter):
        """ set a completer to autocomplete value """
        self.edit.setCompleter(completer)


class ComboField(BaseField):
    """Editor for string value

    Attributes:
        edit (QLineEdit)
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.edit = QComboBox()
        self.edit.setEditable(True)
        self.edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.set_widget(self.edit)

    def set_value(self, value: str):
        self.edit.setCurrentText(str(value))

    def get_value(self):
        """Return quoted string
            ..todo : check if quotes are required
        """
        return self.edit.currentText()

    def addItems(self, words: list):
        """ set a completer to autocomplete value """
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
        self.box.addItem("False", False)
        self.box.addItem("True", True)
        self.set_widget(self.box)
        self.box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def set_value(self, value: bool):
        self.box.setCurrentIndex(int(value))

    def get_value(self) -> bool:
        return self.box.currentData()


class OperatorField(BaseField):
    """Editor for Logic Value (less, greater, more than etc ...)

    Attributes:
        combo_box (QComboBox
    """

    SYMBOL = (
        ("less", "<"),
        ("less or equal", "<="),
        ("greater", ">"),
        ("greater or equal", ">="),
        ("equal", "="),
        ("not equal", "!="),
        ("like", "LIKE"),
        ("regex", "~"),
        ("in", "IN"),
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        self.combo_box = QComboBox()
        self.set_widget(self.combo_box)
        self.combo_box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self._fill()

    def set_value(self, value: str):
        self.combo_box.setCurrentText(value)

    def get_value(self) -> str:
        return self.combo_box.currentData()

    def _fill(self):
        """ Fill QComboBox with SYMBOL """
        self.combo_box.clear()
        for s in self.SYMBOL:
            self.combo_box.addItem(s[0], s[1])


class LogicField(BaseField):

    """ Editor for logic field (And/Or)
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.box = QComboBox()

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
        return self.box.currentData()


class FieldFactory(QObject):
    """FieldFactory is a factory to build BaseEditor according sql Field data

    Attributes:
        conn (sqlite3.connection)

    """

    def __init__(self, conn):
        self.conn = conn

    def create(self, sql_field):
        # sample fields are stored as tuples
        # if type(sql_field) is tuple:
        #     sample = sql_field[1]
        #     sql_field = sql_field[2]
        # else:
        #     # Passing sample has no effect for non-sample fields
        #     sample = None

        field = sql.get_field_by_name(self.conn, sql_field)

        # if field["name"] == "gt":
        #     w = GenotypeField()
        #     return w
        if field["type"] == "int":
            w = IntegerField()
            # w.set_range(*sql.get_field_range(self.conn, sql_field, sample))
            return w

        if field["type"] == "float":
            w = FloatField()
            # w.set_range(*sql.get_field_range(self.conn, sql_field, sample))
            return w

        if field["type"] == "str":
            w = StrField()
            return w

        if field["type"] == "bool":
            w = BoolField()
            return w

        return StrField()


class FilterItem(object):
    """FilterItem is a recursive class which represent item for a FilterModel
    A tree of FilterItem can be store by adding FilterItem recursively as children.
    Each FilterItem has a parent and a list of children.
    see https://doc.qt.io/qt-5/qtwidgets-itemviews-simpletreemodel-example.html

    :Attributes:
        parent (FilterItem)
        children (list of FilterItem)
    :Example:
    root = FilterItem() # Create rootItem
    root.append(FilterItem()) # Append 2 children
    root.append(FilterItem())
    root[0].append(FilterItem()) # Append 1 child to the first children
    """

    LOGIC_TYPE = 0  #  Logic type is AND/OR/XOR
    CONDITION_TYPE = 1  #  Condition type is (field, operator, value)

    def __init__(self, data=None, parent=None):
        """FilterItem constructor with parent as FilterItem parent

        Args:
            data (any): str (logicType) or tuple (ConditionType).
            parent (FilterItem): item's parent
            children(list<FilterItem>): list of children
        """
        self.parent = parent
        self.children = []
        self.data = data
        self.uuid = str(uuid.uuid1())
        self.checked = True

    def __del__(self):
        """ FilterItem destructor """
        self.children.clear()

    def __repr__(self):
        return f"Filter Item {self.data}"

    def __getitem__(self, row):
        """Return child

        Args:
            row (int): child position

        Returns:
            FilterItem
        """
        return self.children[row]

    def append(self, item):
        """Append child

        Args:
            item (FilterItem)
        """
        item.parent = self
        self.children.append(item)

    def insert(self, row: int, item):
        """insert child at a specific location

        Args:
            row (int): child index
            item (FilterItem)
        """
        item.parent = self
        self.children.insert(row, item)

    def remove(self, row: int):
        """Remove child from a specific position

        Args:
            index (int): child index
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
            child.setRecursiveChecked(checked)

    def type(self):
        """Return item type.
            ..todo : maybe create subclass for each types ?

        Returns:
            LOGIC_TYPE or CONDITION_TYPE
        """
        if isinstance(self.data, str):  #  Logic
            return self.LOGIC_TYPE

        if isinstance(self.data, tuple):  #  condition
            return self.CONDITION_TYPE

        return None

    def get_field(self):
        if self.type() == self.CONDITION_TYPE:
            return self.data[0]
        return None

    def get_operator(self):
        if self.type() == self.CONDITION_TYPE:
            return self.data[1]
        return None

    def get_value(self):
        if self.type() == self.CONDITION_TYPE:
            return self.data[2]

        if self.type() == self.LOGIC_TYPE:
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
    #     #     if self.type() == self.LOGIC_TYPE:
    #     #         return self.data

    #     #     if self.type() == self.CONDITION_TYPE:
    #     #         return self.data[column - 1]

    def set_field(self, data):
        if self.type() == self.CONDITION_TYPE:
            tmp = list(self.data)
            tmp[0] = data
            self.data = tuple(tmp)

    def set_operator(self, data):
        if self.type() == self.CONDITION_TYPE:
            tmp = list(self.data)
            tmp[1] = data
            self.data = tuple(tmp)

    def set_value(self, data):
        if self.type() == self.CONDITION_TYPE:
            tmp = list(self.data)
            tmp[2] = data
            self.data = tuple(tmp)

        if self.type() == self.LOGIC_TYPE:
            self.data = data


class FilterModel(QAbstractItemModel):

    """Model to display filter from Query.filter.
    The model store Query filter as a nested tree of FilterItem.
    You can access data from self.item() and edit model using self.set_data() and helper method like
    self.add_logic_item, self.add_condition_item and remove_item.
    Attributes:
        conn (sqlite3.connection): sqlite3 connection
        filterChanged (Signal): signal emited when model is edited.
        root_item (FilterItem): RootItem (invisible) to store recursive item=

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

    # Custom type to get FilterItem.type(). See self.data()
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
        """Model destructor.
        """
        del self.root_item

    def data(self, index: QModelIndex, role):
        """Overrided Qt methods : Return model's data according index and role

        Args:
            index (QModelIndex): index of item
            role (Qt.Role)

        Returns:
            Any type: Return value
        """
        if not index.isValid():
            return None

        if role == Qt.DisplayRole or role == Qt.EditRole:
            item = self.item(index)
            if index.column() == 0:
                return str(item.checked)

            if index.column() == 1:
                if item.type() == FilterItem.CONDITION_TYPE:
                    return str(item.get_field())
                if item.type() == FilterItem.LOGIC_TYPE:
                    return str(item.get_value())

            if index.column() == 2:
                if item.type() == FilterItem.CONDITION_TYPE:
                    return str(item.get_operator())

            if index.column() == 3:
                if item.type() == FilterItem.CONDITION_TYPE:
                    return str(item.get_value())

        if role == FilterModel.TypeRole:
            # Return item type
            return self.item(index).type()

        if role == FilterModel.UniqueIdRole:
            return self.item(index).uuid

        return None

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
        #     if self.item(index).type() == FilterItem.LOGIC_TYPE:
        #         font = QFont()
        #         font.setBold(True)
        #         return font

    def setData(self, index, value, role=Qt.EditRole):
        """Overrided Qt methods: Set data according index and value.
        This methods is called from FilterDelegate when edition has been done

        Args:
            index (QModelIndex)
            value (any): new value
            role (Qt.Role)

        Returns:
            bool: Return True if success otherwise return False
        """

        if role == Qt.EditRole:
            if index.isValid():
                item = self.item(index)

                if index.column() == 0:
                    item.checked = bool(value)

                if index.column() == 1:
                    if item.type() == FilterItem.LOGIC_TYPE:
                        item.set_value(value)

                    if item.type() == FilterItem.CONDITION_TYPE:
                        item.set_field(value)

                if index.column() == 2 and item.type() == FilterItem.CONDITION_TYPE:
                    item.set_operator(value)

                if index.column() == 3 and item.type() == FilterItem.CONDITION_TYPE:
                    item.set_value(value)

                self.filtersChanged.emit()
                return True

        if role == Qt.CheckStateRole:
            if index.isValid():
                self.setRecursiveChecked(index, bool(value))
                self.filtersChanged.emit()

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

        return None

    def index(self, row, column, parent=QModelIndex()) -> QModelIndex:
        """ Overrided Qt methods: create index according row, column and parent """

        if not self.hasIndex(row, column, parent):
            return QModelIndex()

        if not parent.isValid():  #  If no parent, then parent is the root item
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
        """Clear Model
        """
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
        if len(data):
            self.root_item.append(self.to_item(data))
        self.endResetModel()

    def to_item(self, data: dict) -> FilterItem:
        """ recursive function to build a nested FilterItem structure from dict data """
        if len(data) == 1:  #  logic item
            operator = list(data.keys())[0]
            item = FilterItem(operator)
            [item.append(self.to_item(k)) for k in data[operator]]
            return item
        else:  # condition item
            item = FilterItem((data["field"], data["operator"], data["value"]))
            return item

    def to_dict(self, item=None) -> dict:
        """ recursive function to build a nested dictionnary from FilterItem structure"""

        if len(self.root_item.children) == 0:
            return {}

        if item is None:
            item = self.root_item[0]

        if item.type() == FilterItem.LOGIC_TYPE and item.checked is True:
            # Return dict with operator as key and item as value
            operator_data = [
                self.to_dict(child) for child in item.children if child.checked is True
            ]
            return {item.get_value(): operator_data}

        if item.type() == FilterItem.CONDITION_TYPE:
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
            value (tuple): tuple (field, operator, value)
            parent (QModelIndex): Parent index
        """

        #  Skip if parent is a condition type
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
        """ Overrided Qt methods: return row count according parent """

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

    def flags(super, index) -> Qt.ItemFlags:
        """ Overrided Qt methods: return Qt flags to make item editable and selectable """

        if not index.isValid():
            return 0

        item = index.internalPointer()

        if index.column() == 0 or index.column() == 4:
            return Qt.ItemIsSelectable | Qt.ItemIsEnabled

        if item.type() == FilterItem.LOGIC_TYPE and index.column() != 1:
            return Qt.ItemIsSelectable | Qt.ItemIsEnabled

        if item.type() == FilterItem.LOGIC_TYPE and index.column() == 1:
            return (
                Qt.ItemIsSelectable
                | Qt.ItemIsEditable
                | Qt.ItemIsEnabled
                | Qt.ItemIsDragEnabled
                | Qt.ItemIsDropEnabled
            )

        if item.type() == FilterItem.CONDITION_TYPE:
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
        Actually, it serializes only the first index from t he list.
        Args:
            indexes (list<QModelIndex>)

        Returns:
            QMimeData
            ..see: self.dropMimeData
        """
        data = QMimeData(self._MIMEDATA)

        if not indexes:
            return
        else:
            index = indexes[0]

        serialization = QByteArray(pickle.dumps(self.item(indexes[0])))
        data.setData(self._MIMEDATA, serialization)
        return data

    def setRecursiveChecked(self, index, checked=True):

        if not index.isValid():
            return

        item = self.item(index)

        item.checked = checked
        start = self.index(index.row(), 0, index.parent())
        end = self.index(index.row(), self.columnCount() - 1, index.parent())

        self.dataChanged.emit(start, end)

        for row in range(self.rowCount(index)):
            cindex = self.index(row, 0, index)
            self.setRecursiveChecked(cindex, checked)


class FilterDelegate(QStyledItemDelegate):

    """FilterDelegate is used to create widget editor for the model inside the view.
    Without a delegate, the view cannot display editor when user double clicked on a cell

    Based editor are created from self.createEditor.
    FilterModel data are readed and writeed from setEditorData and setModelData
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
        """Overrided from Qt. Create an editor

        Args:
            parent (QWidget): widget's parent
            option (QStyleOptionViewItem)
            index (QModelIndex)

        Returns:
            QWidget: a editor with set_value and get_value methods
        """
        # return super().createEditor(parent,option,index)
        model = index.model()
        item = model.item(index)
        conn = model.conn

        if index.column() == 1:
            if item.type() == FilterItem.LOGIC_TYPE:
                return LogicField(parent)

            if item.type() == FilterItem.CONDITION_TYPE:
                w = ComboField(parent)
                w.addItems([i["name"] for i in prepare_fields(conn)])
                return w

        if index.column() == 2:
            w = OperatorField(parent)
            return w

        if index.column() == 3:
            return StrField(parent)

        return super().createEditor(parent, option, index)

    def setEditorData(self, editor: QWidget, index: QModelIndex):
        """Overrided from Qt. Read data from model and set editor data
        Actually, it calls BaseEditor.set_value() methods

        Args:
            editor (QWidget)
            index (QModelindex)
        """
        editor.set_value(index.data(Qt.EditRole))
        # super().setEditorData(editor, index)

    def editorEvent(self, event: QEvent, model, option, index: QModelIndex):

        if not index.isValid():
            return False

        if event.type() == QEvent.MouseButtonPress:

            item = model.item(index)

            if index.column() == self.COLUMN_CHECKBOX and self._check_rect(
                option.rect
            ).contains(event.pos()):
                model.setData(index, not item.checked, Qt.CheckStateRole)
                return True

            if index.column() == self.COLUMN_REMOVE and self._check_rect(
                option.rect
            ).contains(event.pos()):
                model.remove_item(index)
                return True

        return super().editorEvent(event, model, option, index)

    def setModelData(self, editor, model, index):
        """Overrided from Qt. Read data from editor and set the model data
        Actually, it calls editor.set_value()

        Args:
            editor (QWidget): editor
            model (FilterModel)
            index (QModelindex)
        """
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
            painter.drawPixmap(rect.x(), rect.y(), check_icon.pixmap(self.icon_size))

        if index.column() > self.COLUMN_CHECKBOX:

            font = QFont()
            align = Qt.AlignVCenter
            color = option.palette.color(
                QPalette.Normal if item.checked else QPalette.Disabled,
                QPalette.HighlightedText if is_selected else QPalette.WindowText,
            )

            if item.type() == FilterItem.LOGIC_TYPE:
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

        # if index.column() == 3 and item.type() == FilterItem.LOGIC_TYPE:
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


class FiltersEditorWidget(plugin.PluginWidget):

    ENABLE = True
    changed = Signal()

    def __init__(self, conn=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Filter"))
        self.view = QTreeView()
        # conn is always None here but initialized in on_open_project()
        self.model = FilterModel(conn)
        self.delegate = FilterDelegate()
        self.toolbar = QToolBar()
        self.toolbar.setIconSize(QSize(16, 16))
        # self.toolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)

        self.view.setModel(self.model)
        self.view.setItemDelegate(self.delegate)
        self.view.setDragEnabled(True)
        self.view.header().setStretchLastSection(False)
        self.view.setAcceptDrops(True)
        self.view.setDragDropMode(QAbstractItemView.InternalMove)
        self.view.setAlternatingRowColors(True)
        self.view.setIndentation(0)
        # self.view.setItemsExpandable(False)
        # self.view.setRootIsDecorated(False)

        self.view.header().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.view.header().setSectionResizeMode(1, QHeaderView.Stretch)
        self.view.header().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.view.header().setSectionResizeMode(3, QHeaderView.Stretch)
        self.view.header().setSectionResizeMode(4, QHeaderView.ResizeToContents)

        self.view.header().hide()

        self.combo = QComboBox()
        self.combo.addItem("")
        self.combo.setMinimumHeight(30)
        self.combo.currentTextChanged.connect(self.on_combo_changed)
        self.save_button = QToolButton()
        self.save_button.setIcon(FIcon(0xF0193))
        # self.save_button.setAutoRaise(True)
        self.save_button.setMinimumHeight(30)
        self.save_button.clicked.connect(self.on_save_filters)

        hlayout = QHBoxLayout()
        hlayout.addWidget(self.combo)
        hlayout.addWidget(self.save_button)

        layout = QVBoxLayout()
        layout.addLayout(hlayout)
        layout.addWidget(self.view)
        layout.addWidget(self.toolbar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(1)
        self.setLayout(layout)
        # self.model.filterChanged.connect(self.on_filter_changed)

        # setup Menu

        self.toolbar.addAction(FIcon(0xF0415), "Add Condition", self.on_add_condition)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        # self.toolbar.addAction(FIcon(0xF5E8), "delete", self.on_delete_item)

        # self.view.selectionModel().currentChanged.connect(self.on_filters_changed)
        self.model.filtersChanged.connect(self.on_filters_changed)

    def set_add_icon(self, icon: QIcon):
        self.delegate.add_icon = icon

    def set_rem_icon(self, icon: QIcon):
        self.delegate.rem_icon = icon

    @property
    def filters(self):
        return self.model.filters

    @filters.setter
    def filters(self, filters):
        self.model.filters = filters

    def on_register(self, mainwindow):
        """ Overrided from PluginWidget """
        pass

    def on_open_project(self, conn):
        """ Overrided from PluginWidget """
        self.model.conn = conn
        self.on_refresh()

    def on_refresh(self):
        """ Overrided """
        self.model.filters = self.mainwindow.state.filters
        self._update_view_geometry()

    def on_filters_changed(self):

        """ triggered when filter has changed """

        if self.mainwindow:
            self.mainwindow.state.filters = self.model.filters
            self.mainwindow.refresh_plugins(sender=self)

    def on_add_logic(self):
        """Add logic item to the current selected index
        """
        index = self.view.currentIndex()
        if index:
            self.model.add_logic_item(parent=index)
            # self.view.setFirstColumnSpanned(0, index.parent(), True)

        self._update_view_geometry()

    def on_save_filters(self):

        # TODO : MANAGE PLUGINS SETTINGS
        name, _ = QInputDialog.getText(self, "Filter name", "Filter Name")
        self.combo.addItem(name, self.filters)

    def on_combo_changed(self):

        data = self.combo.currentData()
        if data:
            self.filters = data
            self.on_filters_changed()
            self._update_view_geometry()
        else:
            self.model.clear()
            self._update_view_geometry()

    def _update_view_geometry(self):
        """Set column Spanned to True for all Logic Item
        This allows Logic Item Editor to take all the space inside the row
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
        """Add condition item to the current selected index
        """
        index = self.view.currentIndex()

        if index.isValid():
            if self.model.item(index).type() == FilterItem.LOGIC_TYPE:
                self.model.add_condition_item(parent=index)

        else:
            if self.model.rowCount() == 0:
                self.model.add_logic_item(parent=QModelIndex())
                gpindex = self.model.index(0, 0, QModelIndex())
                self.model.add_condition_item(parent=gpindex)

        self._update_view_geometry()

    def on_open_condition_dialog(self):
        """Open the condition creation dialog
        """
        dialog = FieldDialog(conn=self.conn, parent=self)
        if dialog.exec_() == dialog.Accepted:
            cond = dialog.get_condition()
            index = self.view.currentIndex()
            if index:
                self.model.add_condition_item(parent=index, value=cond)

    def on_delete_item(self):
        """Delete current item
        """
        ret = QMessageBox.question(
            self,
            "remove row",
            "Are you to remove this item ? ",
            QMessageBox.Yes | QMessageBox.No,
        )

        if ret == QMessageBox.Yes:
            self.model.remove_item(self.view.currentIndex())

    def on_selection_changed(self):
        """ Enable/Disable add button depending item type """

        index = self.view.currentIndex()
        if self.model.item(index).type() == FilterItem.CONDITION_TYPE:
            self.add_button.setDisabled(True)
        else:
            self.add_button.setDisabled(False)

    def contextMenuEvent(self, event: QContextMenuEvent):

        pos = self.view.viewport().mapFromGlobal(event.globalPos())
        index = self.view.indexAt(pos)

        if index.isValid():
            menu = QMenu(self)

            item = self.model.item(index)
            if item.type() == FilterItem.LOGIC_TYPE:
                menu.addAction("Add condition", self.on_add_condition)
                menu.addAction("Add group", self.on_add_logic)

            menu.exec_(event.globalPos())


if __name__ == "__main__":

    app = QApplication(sys.argv)
    app.setStyle("fusion")

    style.dark(app)

    from cutevariant.core.importer import import_reader
    from cutevariant.core.reader import FakeReader
    import os

    from cutevariant.gui.ficon import FIcon, setFontPath

    setFontPath(os.path.join("../../materialdesignicons-webfont.ttf"))

    conn = sql.get_sql_connexion(":memory:")
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

    view.set_add_icon(FIcon(0xF0419))
    view.set_rem_icon(FIcon(0xF0419))
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
