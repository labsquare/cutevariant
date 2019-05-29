from PySide2.QtWidgets import * 
from PySide2.QtCore import * 
from PySide2.QtGui import * 
import sys
from cutevariant.gui import style
# Some fields editors 

from cutevariant.core import sql, get_sql_connexion

class BaseField(QFrame):
    """Base class for Field widget """
    def __init__(self, parent = None):
        super().__init__(parent)
        self.setAutoFillBackground(True)
        self.setBackgroundRole(QPalette.Highlight)

    def set_value(self, value):
        raise NotImplemented()

    def get_value(self):
        raise NotImplemented()



class IntegerField(BaseField):
    """Field with a slider and a spin box to edit integer value """
    def __init__(self, parent = None):
        super().__init__(parent)
        self.spin_box = QSpinBox()
        h_layout = QHBoxLayout()
        h_layout.addWidget(self.spin_box)
        h_layout.setContentsMargins(0,0,0,0)
        self.setLayout(h_layout)

    def set_value(self, value: int):
        self.spin_box.setValue(value)

    def get_value(self) -> int:
        return self.spin_box.value()

    def set_range(self, min_, max_):
        self.spin_box.setRange(min_,max_)


class FloatField(BaseField):
    """Field with a spin_box and a spin box to edit integer value """
    def __init__(self, parent = None):
        super().__init__(parent)
        self.spin_box = QDoubleSpinBox()
        h_layout = QHBoxLayout()
        h_layout.addWidget(self.spin_box)
        self.setLayout(h_layout)

        self.spin_box.valueChanged.connect(self._show_tooltip)

    def set_value(self, value: int):
        self.spin_box.setValue(value)

    def get_value(self) -> int:
        return self.spin_box.value()

    def set_range(self, min_, max_):
        self.spin_box.setRange(min_,max_)

    def _show_tooltip(self, value):

        tip = QToolTip()
        pos = self.mapToGlobal(self.spin_box.pos() + QPoint(self.spin_box.width() / 2, 0))
        tip.showText(pos, str(value))


class StrField(BaseField):
    """docstring for ClassName"""
    def __init__(self, parent = None):
        super().__init__(parent)
        self.edit = QLineEdit()
        h_layout = QHBoxLayout()
        h_layout.addWidget(self.edit)
        self.setLayout(h_layout)

    def set_value(self, value:str):
        self.edit.setText(value)  

    def get_value(self) -> str:
        return self.edit.text()

    def set_completer(self, completer: QCompleter):
        self.edit.setCompleter(completer)

class BoolField(BaseField):
    """docstring for ClassName"""
    def __init__(self, parent = None):
        super().__init__(parent)
        self.box = QCheckBox()
        h_layout = QHBoxLayout()
        h_layout.addWidget(self.box)
        self.setLayout(h_layout)


    def set_value(self, value:bool):
        self.box.setValue(value) 

    def get_value(self) -> bool:
        return self.box.value()


class OperatorField(BaseField):
    """docstring for ClassName"""

    SYMBOL = (
        ("less", "<"),
        ("less or equal", "<="),
        ("greater", ">"),
        ("greater or equal", ">="),
        ("equal", "=="),
        ("not equal", "!=")
        )

    def __init__(self, parent = None):
        super().__init__(parent)

        h_layout = QHBoxLayout()
        self.combo_box = QComboBox()
        h_layout.addWidget(self.combo_box)
        h_layout.setContentsMargins(0,0,0,0)
        self.setLayout(h_layout)
        self.fill()

    def set_value(self, value):
        pass 

    def get_value(self):
        pass 

    def fill(self):
        self.combo_box.clear()
        for s in self.SYMBOL:
            self.combo_box.addItem(s[0], s[1])

class ColumnField(BaseField):
    """docstring for ClassName"""
    def __init__(self, parent = None):
        super().__init__(parent)
        self.combo_box = QComboBox()
        h_layout = QHBoxLayout()
        h_layout.addWidget(self.combo_box)
        h_layout.setContentsMargins(0,0,0,0)
        self.combo_box.setEditable(True)
        self.setLayout(h_layout)

    def set_value(self, value):
        pass 

    def get_value(self):
        pass 

    def set_columns(self, columns: list):
        self.combo_box.addItems(columns)




class FieldBuilder(QObject):

    def __init__(self, conn):
        self.conn = conn

    def create(self, sql_field):
        field = sql.get_field_by_name(self.conn, sql_field)
        print(field)
        if field["type"] == 'int':
            
            w = IntegerField()
            w.set_range(*sql.get_field_range(conn,sql_field))
            return w

        if field["type"] == 'float':
            w = FloatField()
            w.set_range(*sql.get_field_range(conn,sql_field))
            return w

        if field["type"] == 'str':
            w = StrField()
            unique_values = sql.get_field_unique_values(conn,"gene") # Can be huge ... How to use "like" ??
            w.set_completer(QCompleter(unique_values))
            return w

        if field["type"] == 'bool':
            w = BoolField()
            return w


        return StrField()



class ToggleButton(BaseField):
    def __init__(self, parent = None):
        super().__init__(parent)

        tool = QPushButton("AND")
        tool1 = QPushButton("OR")

        tool1.setCheckable(True)
        tool.setCheckable(True)

        tool1.setChecked(True)


        # tool.setFlat(True)   
        # tool1.setFlat(True)

        g = QButtonGroup(parent)
        g.setExclusive(True)

        g.addButton(tool,0)
        g.addButton(tool1,1)

        h = QHBoxLayout()
        h.addWidget(tool)
        h.addWidget(tool1)

        self.setLayout(h)
        self.setMaximumWidth(100)
        h.setContentsMargins(0,0,0,0)

        tool.setStyleSheet("QPushButton:checked{background-color:red}")
        tool1.setStyleSheet("QPushButton:checked{background-color:red}")


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

    LOGIC_TYPE = 0  # Logic type is AND/OR/XOR
    CONDITION_TYPE = 1 # Condition type is (field, operator, value)

    def __init__(self, data = None, parent = None):
        """ FilterItem constructor with parent as FilterItem parent """ 
        self.parent = parent
        self.children = []  
        self.data = data

    def __del__(self):
        """ FilterItem destructor """
        del self.children

    def __repr__(self):
        return str(self.data)


    def __getitem__(self, row):
        """ Return child from row """ 
        return self.children[row]

    def append(self, item):
        """ Append FilterItem as child """
        item.parent = self
        self.children.append(item)

    def row(self):
        """ Return index of item from his parent. 
        If the item has no parent, it returns 0 """ 
        if self.parent is not None:
            return self.parent.children.index(self)

        return 0

    def type(self):
        if isinstance(self.data, str): # Logic 
            return self.LOGIC_TYPE 

        if isinstance(self.data, tuple): # condition
            return self.CONDITION_TYPE

        return None

    def get_data(self, column = 0):

        if column not in range(0,3):
            return None

        if self.type() == self.LOGIC_TYPE and column == 0:
            return self.data

        if self.type() == self.CONDITION_TYPE:
            return self.data[column]

        return None


class FilterModel(QAbstractItemModel):
    """ FilterModel is the class to store FilterItem for the FilterView 

    """
    def __init__(self, conn, parent=None):
        super().__init__(parent)
        self.root_item = FilterItem()
        self.conn = conn


    def __del__(self):
        del self.root_item

    def data(self, index: QModelIndex, role):
        """ overrided : Return data for the Qt view """ 
        if not index.isValid():
            return None

        if role == Qt.EditRole:
            print("edit ")
            return str("sacha")

        if role == Qt.DisplayRole:
            item = index.internalPointer()
            return item.get_data(index.column())

        if role == Qt.TextAlignmentRole:
            if index.column() == 0:
                return int(Qt.AlignVCenter)+int(Qt.AlignLeft)
            if index.column() == 1:
                return Qt.AlignCenter
            if index.column() == 2:
                return int(Qt.AlignVCenter)+int(Qt.AlignLeft)




        


    def setData(self, index, value, role = Qt.EditRole):

    
        return True



    def index(self, row, column, parent : QModelIndex):
        """ overrided : create index according row, column and parent """ 

        if not self.hasIndex(row,column, parent):
            return QModelIndex() 

        if not parent.isValid(): # If no parent, then parent is the root item 
            parent_item = self.root_item

        else:
            parent_item = parent.internalPointer()

        child_item = parent_item[row]
        if child_item:
            return self.createIndex(row,column, child_item)
        else:
            return QModelIndex()


    def parent(self, index: QModelIndex):
        """overrided : Create parent index """
        if not index.isValid():
            return QModelIndex()

        child_item  = index.internalPointer()
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
        
        self.root_item.append(self.toItem(data))


        self.endResetModel()

    def toItem(self, data: dict) -> FilterItem:
        """ recursive function to load item in tree from data """
        if len(data) == 1:  #  logic item
            operator = list(data.keys())[0]
            item = FilterItem(operator)
            [item.append(self.toItem(k)) for k in data[operator]]
            return item
        else:  # condition item
            item = FilterItem((data["field"], data["operator"], data["value"]))
            return item

        
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
            return Qt.ItemIsSelectable|Qt.ItemIsEditable|Qt.ItemIsEnabled

        if item.type() == FilterItem.CONDITION_TYPE: 
            return Qt.ItemIsSelectable|Qt.ItemIsEditable|Qt.ItemIsEnabled
            
        return Qt.ItemIsSelectable|Qt.ItemIsEditable



class FilterDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)





    def createEditor(self, parent, option, index: QModelIndex):

        item = index.internalPointer()

        conn = index.model().conn

        print(conn)

        if index.column() == 0:
            if item.type() == FilterItem.LOGIC_TYPE:
                return ToggleButton(parent)

            if item.type() == FilterItem.CONDITION_TYPE:
                w = ColumnField(parent)
                columns = [i["name"] for i in sql.get_fields(conn)]
                w.set_columns(columns)
                return w

        if index.column() == 1:
            w =  OperatorField(parent)
            return w

        if index.column() == 2:
            w =  IntegerField(parent)
            return w


        return super().createEditor(parent,option,index)

    def setEditorData(self, editor, index):
        pass 

    def setModelData(self,editor, model, index):
        pass

    def sizeHint(self, option, index: QModelIndex):
        return QSize(super().sizeHint(option,index).width(), 30)
      
    def updateEditorGeometry(self, editor, option,index):
        editor.setGeometry(option.rect)






app = QApplication(sys.argv)
app.setStyle("fusion")

style.dark(app)

conn = get_sql_connexion("/home/schutz/Dev/cutevariant/examples/test.db")


data = {
            "AND": [
                {"field": "chr", "operator": "=", "value": "chr"},
                {
                    "OR": [
                        {"field": "b", "operator": "=", "value": 5},
                        {"field": "c", "operator": "=", "value": 3},
                    ]
                },
            ]
        }

print(data)


model = FilterModel(conn)
model.load(data)
delegate = FilterDelegate()



view = QTreeView()
view.setEditTriggers(QAbstractItemView.DoubleClicked)
view.setItemDelegate(delegate)
view.setAlternatingRowColors(True)
view.setUniformRowHeights(True)
view.setModel(model)

view.setFirstColumnSpanned(0, QModelIndex(), True)

view.show()

app.exec_()





