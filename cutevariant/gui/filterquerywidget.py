from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *
from enum import Enum

from .abstractquerywidget import AbstractQueryWidget
from cutevariant.core import Query


class FilterType(Enum):
    LOGIC = 1
    CONDITION = 2


class FilterItem(QStandardItem):
    def __init__(self, type=FilterType.LOGIC):
        super().__init__()
        self.type = type

        if self.type == FilterType.LOGIC:
            self.name = "AND"

        else:
            self.name = "pos"
            self.operator = ">"
            self.value = 123

    def makeText(self):
        if self.type == FilterType.LOGIC:
            self.setText(self.name)

        if self.type == FilterType.CONDITION:
            self.setText(self.name + self.operator + self.value)


class FilterQueryModel(QStandardItemModel):
    def __init__(self):
        super().__init__()
        self.query = None

    def setQuery(self, query: Query):
        self.query = query
        self.clear()
        if self.query.filter is not None:
            self.appendRow(self.toItem(self.query.filter))

    def getQuery(self) -> Query:
        if self.rowCount() != 0:
            self.query.filter = self.fromItem(self.item(0))
        return self.query

    def toItem(self, data: dict) -> QStandardItem:

        if len(data) == 1:  #  logic item
            operator = list(data.keys())[0]
            item = FilterItem(FilterType.LOGIC)
            item.name = operator
            item.setEditable(False)
            item.makeText()
            for k in data[operator]:
                item.appendRow(self.toItem(k))
            return item
        else:  # condition item
            item = FilterItem(FilterType.CONDITION)
            item.name = str(data["field"])
            item.operator = str(data["operator"])
            item.value = str(data["value"])
            item.makeText()
            return item

    def fromItem(self, item: QStandardItem) -> dict:
        if item.type == FilterType.LOGIC:
            op = item.name
            data = {op: []}

            for i in range(item.rowCount()):
                data[op].append(self.fromItem(item.child(i)))
            return data

        else:
            data = {}
            data["field"] = item.name
            data["operator"] = item.operator
            data["value"] = item.value
            return data


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


class FilterQueryWidget(AbstractQueryWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Filter")
        self.view = QTreeView()
        self.model = FilterQueryModel()
        self.view.setModel(self.model)

        layout = QVBoxLayout()
        layout.addWidget(self.view)
        layout.setContentsMargins(0,0,0,0)

        self.setLayout(layout)

        self.model.itemChanged.connect(self.changed)
        self.view.doubleClicked.connect(self.edit)

    def setQuery(self, query: Query):
        self.model.setQuery(query)

    def getQuery(self) -> Query:
        return self.model.getQuery()

    def edit(self, index):
        dialog = FilterEditDialog(self.model.itemFromIndex(index))

        if dialog.exec_():
            dialog.save()

    def contextMenuEvent(self, event):
        """ override methode """

        menu = QMenu(self)

        pos = self.view.viewport().mapFromGlobal(event.globalPos())
        index = self.view.indexAt(pos)

        if index.isValid() is False:
            logic_action = menu.addAction("add logic")

        else:
            logic_action = menu.addAction("add logic")
            item_action = menu.addAction("add condition")
            menu.addSeparator()
            rem_action = menu.addAction("Remove")

        menu.exec_(event.globalPos())
