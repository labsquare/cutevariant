from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *
import sys
from cutevariant.gui import style
import pickle
import uuid

# Some fields editors

from cutevariant.core import sql, get_sql_connexion


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
        raise NotImplemented()

    def get_value(self):
        raise NotImplemented()

    def set_widget(self, widget):
        """Setup a layout with a widget
        Args:
            widget (QWidget)
        """
        self.widget = widget
        h_layout = QHBoxLayout()
        h_layout.addWidget(widget)
        h_layout.setContentsMargins(0, 0, 0, 0)
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
        self.set_widget(self.edit)

    def set_value(self, value: str):
        self.edit.setText(str(value))

    def get_value(self) -> str:
        """Return quoted string

            ..todo : check if quotes are required 
        """
        return "'" + self.edit.text() + "'"

    def set_completer(self, completer: QCompleter):
        """ set a completer to autocomplete value """
        self.edit.setCompleter(completer)


class BoolField(BaseField):
    """Editor for Boolean value
    
    Attributes:
        box (QCheckBox)
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.box = QCheckBox()
        self.set_widget(self.box)

    def set_value(self, value: bool):
        self.box.setValue(value)

    def get_value(self) -> bool:
        return self.box.value()


class OperatorField(BaseField):
    """Editor for Logic Value (less, greater, more than etc ...)
    
    Attributes:
        combo_box (QCombobox
    """

    SYMBOL = (
        ("less", "<"),
        ("less or equal", "<="),
        ("greater", ">"),
        ("greater or equal", ">="),
        ("equal", "="),
        ("not equal", "!="),
        ("like", "LIKE"),
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        self.combo_box = QComboBox()
        self.set_widget(self.combo_box)
        self._fill()

    def set_value(self, value: str):
        self.combo_box.setCurrentText(value)

    def get_value(self) -> str:
        return self.combo_box.currentData()

    def _fill(self):
        """ Fill QCombobox with SYMBOL """
        self.combo_box.clear()
        for s in self.SYMBOL:
            self.combo_box.addItem(s[0], s[1])


class ColumnField(BaseField):
    """Editor for field name 
    
    Attributes:
        combo_box (QCombobox)
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.combo_box = QComboBox()
        self.combo_box.setEditable(True)
        self.set_widget(self.combo_box)

    def set_value(self, value: str):
        self.combo_box.setCurrentText(value)

    def get_value(self) -> str:
        return self.combo_box.currentText()

    def set_columns(self, columns: list):
        """ fill combobox with columns values 
        """
        self.combo_box.addItems(columns)


class LogicField(BaseField):

    """ Editor for logic field (And/Or)

    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.and_button = QPushButton("AND")
        self.or_button = QPushButton("OR")

        self.and_button.setCheckable(True)
        self.or_button.setCheckable(True)

        self.and_button.setChecked(True)

        group = QButtonGroup(parent)
        group.setExclusive(True)

        group.addButton(self.or_button, 0)
        group.addButton(self.and_button, 1)

        h = QHBoxLayout()
        h.addWidget(self.or_button)
        h.addWidget(self.and_button)

        self.setLayout(h)
        self.setMaximumWidth(100)
        h.setContentsMargins(0, 0, 0, 0)

        self.or_button.setStyleSheet("QPushButton:checked{background-color:red}")
        self.and_button.setStyleSheet("QPushButton:checked{background-color:red}")

    def set_value(self, value: str):
        print("set value", value)
        if value.upper() == "OR":
            self.or_button.setChecked(True)
        else:
            self.and_button.setChecked(True)

    def get_value(self) -> str:
        print("get value", self.or_button.isChecked())
        if self.or_button.isChecked():
            return "OR"
        else:
            return "AND"


class FieldFactory(QObject):
    """FieldFactory is a factory to build BaseEditor according sql Field data 
    
    Attributes:
        conn (sqlite3.connection)
    
    """

    def __init__(self, conn):
        self.conn = conn

    def create(self, sql_field):
        field = sql.get_field_by_name(self.conn, sql_field)

        if field["type"] == "int":
            w = IntegerField()
            w.set_range(*sql.get_field_range(self.conn, sql_field))
            return w

        if field["type"] == "float":
            w = FloatField()
            w.set_range(*sql.get_field_range(self.conn, sql_field))
            return w

        if field["type"] == "str":
            w = StrField()
            print(field)
            unique_values = sql.get_field_unique_values(
                self.conn, field["name"]
            )  #  Can be huge ... How to use "like" ??
            w.set_completer(QCompleter(unique_values))
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
    root.append(FilterItem()) # Append 2 children
    root.append(FilterItem())
    root[0].append(FilterItem()) # Append 1 child to the first children


    """

    LOGIC_TYPE = 0  #  Logic type is AND/OR/XOR
    CONDITION_TYPE = 1  #  Condition type is (field, operator, value)

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

    def type(self):
        """Return item type. 

            ..todo : maybe create subclass for each types ? 
        
        Returns:
            LOGIC_TYPE or CONDITION_TYPE
        """
        if isinstance(self.data, str):  #  Logic
            return self.LOGIC_TYPE

        if isinstance(self.data, tuple):  #  condition
            return self.CONDITION_TYPE

        return None

    def get_data(self, column=0):
        """ get data according columns. 
        
        if item is a LOGIC_FIELD, it return self.data not matter the column. 
        If item is a CONDITION_TYPE, you can select value from tuple according columns. 
        
        column 0: Field name 
        column 1: Field operator
        column 2 : Field value 

        Args:
            column (int)
        
        Returns:
            (any): Data
        """
        if column not in range(0, 3):
            return None

        if self.type() == self.LOGIC_TYPE and column == 0:
            return self.data

        if self.type() == self.CONDITION_TYPE:
            return self.data[column]

        return None

    def set_data(self, data, column=0):
        """Set data of item according column. See self.get_data
        
        Args:
            data (Any type): any data
            column (int): Column Type

            ..see: self.get_data
        """
        if self.type() == self.LOGIC_TYPE and column == 0:
            self.data = data

        if self.type() == self.CONDITION_TYPE:
            tmp = list(self.data)
            tmp[column] = data
            self.data = tuple(tmp)


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

        # Remove item 
        model.remove_item(view.currentIndex())

    """

    # signal definition
    filterChanged = Signal()
    # See self.headerData()
    _HEADERS = ["field", "operator", "value"]
    _MIMEDATA = "application/x-qabstractitemmodeldatalist"

    # Custom type to get FilterItem.type(). See self.data()
    TypeRole = Qt.UserRole + 1
    UniqueIdRole = Qt.UserRole + 2

    def __init__(self, conn, parent=None):
        super().__init__(parent)
        self.root_item = FilterItem("AND")
        self.conn = conn

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
            #  Display data
            item = self.item(index)
            return item.get_data(index.column())

        if role == Qt.TextAlignmentRole:
            #  Adjust text alignement
            if index.column() == 0:
                return int(Qt.AlignVCenter) + int(Qt.AlignLeft)
            if index.column() == 1:
                return Qt.AlignCenter
            if index.column() == 2:
                return int(Qt.AlignVCenter) + int(Qt.AlignLeft)

        if role == Qt.FontRole:
            #  Make LogicItem as bold
            if self.item(index).type() == FilterItem.LOGIC_TYPE:
                font = QFont()
                font.setBold(True)
                return font

        if role == FilterModel.TypeRole:
            # Return item type
            return self.item(index).type()

        if role == FilterModel.UniqueIdRole:
            return self.item(index).uuid

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
                item.set_data(value, index.column())
                self.filterChanged.emit()
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

        if not parent.isValid():  #  If no parent, then parent is the root item
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
        if len(data) == 1:  #  logic item
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

        if item.type() == FilterItem.LOGIC_TYPE:
            # Return dict with operator as key and item as value
            operator_data = [self.to_dict(child) for child in item.children]
            return {item.get_data(0): operator_data}

        if item.type() == FilterItem.CONDITION_TYPE:
            return {
                "field": item.get_data(0),
                "operator": item.get_data(1),
                "value": item.get_data(2),
            }

    def add_logic_item(self, value="AND", parent=QModelIndex()):
        """Add logic item
        
        Args:
            value (str): Can be "AND" or "OR"
            parent (QModelIndex): parent index 
        """

        #  Skip if parent is a condition type
        if self.item(parent).type == FilterItem.CONDITION_TYPE:
            return

        self.beginInsertRows(parent, 0, 0)
        self.item(parent).insert(0, FilterItem(data=value))
        self.endInsertRows()
        self.filterChanged.emit()

    def add_condition_item(self, value=("chr", ">", "100"), parent=QModelIndex()):
        """Add condition item 
        
        Args:
            value (tuple): tuple (field, operator, value)
            parent (QModelIndex): Parent index
        """

        #  Skip if parent is a condition type
        if self.item(parent).type == FilterItem.CONDITION_TYPE:
            return

        self.beginInsertRows(parent, 0, 0)
        self.item(parent).insert(0, FilterItem(data=value))
        self.endInsertRows()
        self.filterChanged.emit()

    def remove_item(self, index):
        """Remove Item 
        Args:
            index (QModelIndex): item index 
        """
        self.beginRemoveRows(index.parent(), index.row(), index.row())
        self.item(index).parent.remove(index.row())
        self.endRemoveRows()
        self.filterChanged.emit()

    def rowCount(self, parent: QModelIndex) -> int:
        """ Overrided Qt methods: return row count according parent """

        if not parent.isValid():
            parent_item = self.root_item

        else:
            parent_item = parent.internalPointer()

        return len(parent_item.children)

    def columnCount(self, parent: QModelIndex) -> int:
        """ Overrided Qt methods: return column count according parent """
        return 3

    def flags(super, index) -> Qt.ItemFlags:
        """ Overrided Qt methods: return Qt flags to make item editable and selectable """

        if not index.isValid():
            return 0

        item = index.internalPointer()

        if item.type() == FilterItem.LOGIC_TYPE and index.column() == 0:
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

        return Qt.ItemIsSelectable | Qt.ItemIsEditable

    def item(self, index) -> FilterItem:
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

        #  if destination is - 1, it's mean we should append the item at the end of children
        if destinationChild < 0:
            if sourceParent == destinationParent:
                return False
            else:
                destinationChild = len(parent_destination_item.children)

        # Don't move same same Item
        if sourceParent == destinationParent and sourceRow == destinationChild:
            return False

        print("pass")

        self.beginMoveRows(
            sourceParent, sourceRow, sourceRow, destinationParent, destinationChild
        )
        item = parent_source_item.children.pop(sourceRow)
        parent_destination_item.insert(destinationChild, item)
        self.endMoveRows()

        self.filterChanged.emit()
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

    def __init__(self, parent=None):
        super().__init__(parent)

    def createEditor(self, parent, option, index: QModelIndex) -> QWidget:
        """Overrided from Qt. Create an editor 
        
        Args:
            parent (QWidget): widget's parent 
            option (QStyleOptionViewItem)
            index (QModelIndex)
        
        Returns:
            QWidget: a editor with set_value and get_value methods
        """
        model = index.model()
        item = model.item(index)
        conn = model.conn

        if index.column() == 0:
            if item.type() == FilterItem.LOGIC_TYPE:
                return LogicField(parent)

            if item.type() == FilterItem.CONDITION_TYPE:
                w = ColumnField(parent)
                columns = [i["name"] for i in sql.get_fields(conn)]
                w.set_columns(columns)
                return w

        if index.column() == 1:
            w = OperatorField(parent)
            return w

        if index.column() == 2:

            sql_field_index = model.index(index.row(), 0, index.parent())
            sql_field = model.data(sql_field_index, Qt.DisplayRole)
            w = FieldFactory(conn).create(sql_field)
            w.setParent(parent)
            return w

        return super().createEditor(parent, option, index)

    def setEditorData(self, editor: QWidget, index: QModelIndex):
        """Overrided from Qt. Read data from model and set editor data

        Actually, it calls BaseEditor.set_value() methods 
        
        Args:
            editor (QWidget)
            index (QModelindex)
        """
        editor.set_value(index.data(Qt.EditRole))

    def setModelData(self, editor, model, index):
        """Overrided from Qt. Read data from editor and set the model data 

        Actually, it calls editor.set_value() 
        
        Args:
            editor (QWidget): editor 
            model (FilterModel)
            index (QModelindex)
        """
        model.setData(index, editor.get_value())

    def sizeHint(self, option, index: QModelIndex) -> QSize:
        """Overrided from Qt. Return size of row 
        
        Args:
            option (QStyleOptionViewItem )
            index (QModelIndex)
        
        Returns:
            TYPE: Description
        """
        return QSize(super().sizeHint(option, index).width(), 30)

    def updateEditorGeometry(self, editor, option, index):
        """Overrided from Qt. Set editor geometry
        
        Args:
            editor (QWidget)
            option (QStyleOptionViewItem)
            index (QModelIndex)
        """
        editor.setGeometry(option.rect)


if __name__ == "__main__":

    app = QApplication(sys.argv)
    app.setStyle("fusion")

    style.dark(app)

    conn = get_sql_connexion("/home/sacha/Dev/cutevariant/examples/test.db")

    data = {
        "AND": [
            {"field": "chr", "operator": "=", "value": "chr"},
            {
                "OR": [
                    {"field": "i0", "operator": "=", "value": 5},
                    {"field": "i1", "operator": "=", "value": 3},
                    {"field": "i2", "operator": "=", "value": 3},
                ]
            },
        ]
    }

    model = FilterModel(conn)
    model.load(data)
    delegate = FilterDelegate()

    print(model.to_dict(model.root_item[0]))

    view = QTreeView()
    view.setEditTriggers(QAbstractItemView.DoubleClicked)
    view.setItemDelegate(delegate)
    view.setAlternatingRowColors(True)
    view.setUniformRowHeights(True)
    view.setModel(model)
    view.setAcceptDrops(True)
    view.setDragEnabled(True)
    view.setDropIndicatorShown(True)
    view.setSelectionBehavior(QAbstractItemView.SelectRows)
    view.setDragDropMode(QAbstractItemView.InternalMove)

    view.setFirstColumnSpanned(0, QModelIndex(), True)
    view.resize(500, 500)
    view.show()
    view.expandAll()

    app.exec_()
