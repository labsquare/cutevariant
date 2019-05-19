from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *
from enum import Enum

from .plugin import QueryPluginWidget
from cutevariant.core import Query
from cutevariant.gui.ficon import FIcon


class FilterType(Enum):
    LOGIC = 1
    CONDITION = 2


class LogicItem(QStandardItem):

    _LOGIC_ICONS = {"AND": 0xF8E0, "OR": 0xF8E4}

    def __init__(self, logic_type="AND"):
        """
        Create a logic Item : OR / AND  
        """
        super().__init__()
        self.logic_type = logic_type
        self.setEditable(False)
        self.set(logic_type)

    def set(self, logic_type):
        self.setIcon(FIcon(LogicItem._LOGIC_ICONS[self.logic_type]))
        self.setText(logic_type)


class FieldItem(QStandardItem):
    def __init__(self, name, operator, value):
        super().__init__()
        self.setEditable(False)
        self.set(name, operator, value)

    def set(self, name, operator, value):
        self.name = name
        self.operator = operator
        self.value = value
        self.setText(f"{self.name}  {self.operator}  {self.value}")


class FilterQueryModel(QStandardItemModel):
    def __init__(self):
        super().__init__()
        self._query = None

    @property
    def query(self) -> Query:
        if self.rowCount() != 0:
            self._query.filter = self.fromItem(self.item(0))
        return self._query

    @query.setter
    def query(self, query: Query):
        self._query = query

    def load(self):
        self.clear()
        if self._query.filter:
            self.appendRow(self.toItem(self._query.filter))

    def toItem(self, data: dict) -> QStandardItem:
        """ recursive function to load item in tree from data """
        if len(data) == 1:  #  logic item
            operator = list(data.keys())[0]
            item = LogicItem(operator)
            [item.appendRow(self.toItem(k)) for k in data[operator]]
            return item
        else:  # condition item
            item = FieldItem(data["field"], data["operator"], data["value"])
            return item

    def fromItem(self, item: QStandardItem) -> dict:
        """ recursive fonction to get items from tree """
        if isinstance(item, LogicItem):
            # Return dict with operator as key and item as value
            operator_data = [
                self.fromItem(item.child(i)) for i in range(item.rowCount())
            ]
            return {item.logic_type: operator_data}
        else:
            return {"field": item.name, "operator": item.operator, "value": item.value}


class FilterEditDialog(QDialog):
    def __init__(self, item: QStandardItem):
        super().__init__()
        self.field = QLineEdit()
        self.operator = QLineEdit()
        self.value = QLineEdit()
        self.item = item

        form_layout = QFormLayout()

        form_layout.addRow("field", self.field)
        form_layout.addRow("operator", self.operator)
        form_layout.addRow("value", self.value)

        layout = QVBoxLayout()
        buttonBox = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttonBox.accepted.connect(self.save)
        buttonBox.rejected.connect(self.close)

        layout.addLayout(form_layout)
        layout.addWidget(buttonBox)
        self.setLayout(layout)

        self.load()

    def load(self):
        self.field.setText(self.item.data(FilterQueryModel.FieldRole))
        self.operator.setText(self.item.data(FilterQueryModel.OperatorRole))
        self.value.setText(self.item.data(FilterQueryModel.ValueRole))

    def save(self):
        self.item.setText(self.field.text() + self.operator.text() + self.value.text())
        self.item.setData("field", FilterQueryModel.TypeRole)
        self.item.setData(self.field.text(), FilterQueryModel.FieldRole)
        self.item.setData(self.operator.text(), FilterQueryModel.OperatorRole)
        self.item.setData(self.value.text(), FilterQueryModel.ValueRole)


class FilterQueryWidget(QueryPluginWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(self.tr("Filter"))
        self.view = QTreeView()
        self.model = FilterQueryModel()
        self.view.setModel(self.model)

        layout = QVBoxLayout()
        layout.addWidget(self.view)
        layout.setContentsMargins(0, 0, 0, 0)

        self.setLayout(layout)

        # self.model.itemChanged.connect(self.changed)
        self.view.doubleClicked.connect(self.edit)

    def on_init_query(self):
        """ Overrided """
        self.model.query = self.query

    def on_change_query(self):
        """ override methods """
        self.model.load()

    def edit(self, index):
        dialog = FilterEditDialog(self.model.itemFromIndex(index))

        if dialog.exec_():
            dialog.save()

    def contextMenuEvent(self, event):
        """ override methode """

        menu = QMenu(self)

        pos = self.view.viewport().mapFromGlobal(event.globalPos())
        index = self.view.indexAt(pos)

        if not index.isValid():
            logic_action = menu.addAction(self.tr("add logic"))

        else:
            logic_action = menu.addAction(self.tr("add logic"))
            item_action = menu.addAction(self.tr("add condition"))
            menu.addSeparator()
            rem_action = menu.addAction(self.tr("Remove"))

        menu.exec_(event.globalPos())
