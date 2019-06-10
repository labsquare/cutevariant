from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *
import sys
from cutevariant.gui import style

# Some fields editors

from cutevariant.core import sql, get_sql_connexion


class BaseField(QFrame):
    """Base class for Field widget
    Inherit from this class if you want a custom field editor 
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
        self.widget = widget
        h_layout = QHBoxLayout()
        h_layout.addWidget(widget)
        h_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(h_layout)


class IntegerField(BaseField):
    """ Editor as a QSpinbox for integer field value 

        ..todo: Create a slider ? 
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
    """ Editor as a QDoubleSpinBoxfor Floating field value """

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
    """Editor as a QLineEditfor String value """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.edit = QLineEdit()
        self.set_widget(self.edit)

    def set_value(self, value: str):
        self.edit.setText(str(value))

    def get_value(self) -> str:
        """Return quoted string
        
        Returns:
            str
        """
        return "'" + self.edit.text() + "'"

    def set_completer(self, completer: QCompleter):
        """ set a completer to autocomplete value """
        self.edit.setCompleter(completer)


class BoolField(BaseField):
    """Editor as a QCheckbox for Boolean value"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.box = QCheckBox()
        self.set_widget(self.box)

    def set_value(self, value: bool):
        self.box.setValue(value)

    def get_value(self) -> bool:
        return self.box.value()


class OperatorField(BaseField):
    """Operator editor as a QCombobox to select operator value """

    SYMBOL = (
        ("less", "<"),
        ("less or equal", "<="),
        ("greater", ">"),
        ("greater or equal", ">="),
        ("equal", "="),
        ("not equal", "!="),
        ("like","LIKE")
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
    """Editor as QCombobox for Columns value aka Field name """

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


class FieldFactory(QObject):
    """FieldFactory is a factory design patern to build fieldEditor according sql Field data 
    
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


class LogicField(BaseField):
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
        """ FilterItem constructor with parent as FilterItem parent """
        self.parent = parent
        self.children = []
        self.data = data

    def __del__(self):
        """ FilterItem destructor """
        self.children.clear()

    def __repr__(self):
        return f"Filter Item {self.data}"

    def __getitem__(self, row):
        """ Return child from row """
        return self.children[row]

    def append(self, item):
        """ Append FilterItem as child """
        item.parent = self
        self.children.append(item)

    def insert(self, index, item):
        """ insert FilterItem as child """
        item.parent = self
        self.children.insert(index, item)

    def remove(self, index):
        """ Remove FilterItem from children """
        del self.children[index]

    def row(self):
        """ Return index of item from his parent. 
        If the item has no parent, it returns 0 """
        if self.parent is not None:
            return self.parent.children.index(self)

        return 0

    def type(self):
        if isinstance(self.data, str):  #  Logic
            return self.LOGIC_TYPE

        if isinstance(self.data, tuple):  #  condition
            return self.CONDITION_TYPE

        return None

    def get_data(self, column=0):
        """Return data of item according column 

        If item is a CONDITION_TYPE, you can select field (column=1), operator (column=2) or value (column=3)
        
        Args:
            column (int)
        
        Returns:
            Any type: Data
        """
        if column not in range(0, 3):
            return None

        if self.type() == self.LOGIC_TYPE and column == 0:
            return self.data

        if self.type() == self.CONDITION_TYPE:
            return self.data[column]

        return None

    def set_data(self, data, column=0):
        """Set data of item according column 
        
        Args:
            data (Any type): any data
            column (int): Column Type
        """
        if self.type() == self.LOGIC_TYPE and column == 0:
            self.data = data

        if self.type() == self.CONDITION_TYPE:
            tmp = list(self.data)
            tmp[column] = data
            self.data = tuple(tmp)


class FilterModel(QAbstractItemModel):

    """Model to store Filter items
    
    Attributes:
        conn (sqlite3.connection)
        root_item (FilterItem): RootItem (invisible) to store recursive item
    """

    filterChanged = Signal()
    HEADERS = ["field", "operator", "value"]
    TypeRole = Qt.UserRole + 1

    def __init__(self, conn, parent=None):
        super().__init__(parent)
        self.root_item = FilterItem()
        self.conn = conn

    def __del__(self):
        del self.root_item

    def data(self, index: QModelIndex, role):
        """return data of model for the Tree View
        
        Args:
            index (QModelIndex): index of item
            role (Qt.Role) 
        
        Returns:
            Any type: Return value  
        """
        if not index.isValid():
            return None

        if role == Qt.DisplayRole or role == Qt.EditRole:
            item = index.internalPointer()
            return item.get_data(index.column())

        if role == Qt.TextAlignmentRole:
            if index.column() == 0:
                return int(Qt.AlignVCenter) + int(Qt.AlignLeft)
            if index.column() == 1:
                return Qt.AlignCenter
            if index.column() == 2:
                return int(Qt.AlignVCenter) + int(Qt.AlignLeft)

        if role == Qt.FontRole:
            if index.internalPointer().type() == FilterItem.LOGIC_TYPE:
                font = QFont()
                font.setBold(True)
                return font


        if role == FilterModel.TypeRole:
            return index.internalPointer().type()

    def setData(self, index, value, role=Qt.EditRole):

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
                return self.HEADERS[section]

        return None

    def index(self, row, column, parent = QModelIndex()):
        """ overrided : create index according row, column and parent """

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

    def parent(self, index: QModelIndex):
        """overrided : Create parent index """
        if not index.isValid():
            return QModelIndex()

        child_item = index.internalPointer()
        parent_item = child_item.parent

        if parent_item == self.root_item:
            return QModelIndex()

        return self.createIndex(parent_item.row(), 0, parent_item)

    def clear(self):
        """ clear all """
        self.root_item.children.clear()

    def load(self, data):
        """ load data from raw dict """
        self.beginResetModel()
        self.clear()
        if len(data):
            self.root_item.append(self.to_item(data))
        self.endResetModel()


    def to_item(self, data: dict) -> FilterItem:
        """ recursive function to load item in tree from data """
        if len(data) == 1:  #  logic item
            operator = list(data.keys())[0]
            item = FilterItem(operator)
            [item.append(self.to_item(k)) for k in data[operator]]
            return item
        else:  # condition item
            item = FilterItem((data["field"], data["operator"], data["value"]))
            return item

    def to_dict(self, item=None) -> dict:
        """ recursive function to export model as a dictionnary """

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

    def rowCount(self, parent: QModelIndex):
        """ overrided : return model row count according parent """

        if not parent.isValid():
            parent_item = self.root_item

        else:
            parent_item = parent.internalPointer()

        return len(parent_item.children)

    def columnCount(self, parent: QModelIndex):
        """ overrided: return column count  according parent """
        return 3

    def flags(super, index) -> Qt.ItemFlags:
        """ overrided : return Qt flags """

        if not index.isValid():
            return 0

        item = index.internalPointer()

        if item.type() == FilterItem.LOGIC_TYPE and index.column() == 0:
            return Qt.ItemIsSelectable | Qt.ItemIsEditable | Qt.ItemIsEnabled

        if item.type() == FilterItem.CONDITION_TYPE:
            return Qt.ItemIsSelectable | Qt.ItemIsEditable | Qt.ItemIsEnabled

        return Qt.ItemIsSelectable | Qt.ItemIsEditable

    def item(self, index) -> FilterItem:
        if index.isValid():
            return index.internalPointer()
        else:
            return self.root_item







class FilterDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)

    def createEditor(self, parent, option, index: QModelIndex):

        item = index.internalPointer()
        model = index.model()
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

    def setEditorData(self, editor, index):
        editor.set_value(index.data(Qt.EditRole))

    def setModelData(self, editor, model, index):
        model.setData(index, editor.get_value())

    def sizeHint(self, option, index: QModelIndex):
        return QSize(super().sizeHint(option, index).width(), 30)

    def updateEditorGeometry(self, editor, option, index):
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
                    {"field": "gene", "operator": "=", "value": 5},
                    {"field": "pos", "operator": "=", "value": 3},
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

    view.setFirstColumnSpanned(0, QModelIndex(), True)

    view.show()

    app.exec_()
