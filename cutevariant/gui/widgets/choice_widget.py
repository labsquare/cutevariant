from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *

from cutevariant.gui.ficon import FIcon


class ChoiceModel(QAbstractListModel):
    def __init__(self, parent=None):
        super().__init__(parent)

        self._data = []

    def rowCount(self, parent=QModelIndex()):
        return len(self._data)

    def data(self, index: QModelIndex, role: Qt.ItemDataRole):

        if not index.isValid():
            return None

        if role == Qt.DisplayRole:
            text = self._data[index.row()]["name"]
            return text

        if role == Qt.DecorationRole:
            return self._data[index.row()]["icon"]

        if role == Qt.CheckStateRole:
            return Qt.Checked if self._data[index.row()]["checked"] else Qt.Unchecked

        if role == Qt.ToolTipRole:
            return self._data[index.row()]["description"]

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:

        return Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsUserCheckable

    def setData(self, index: QModelIndex, value, role: Qt.ItemDataRole):
        """override"""

        if role == Qt.CheckStateRole:
            self._data[index.row()]["checked"] = True if value == Qt.Checked else False
            self.dataChanged.emit(index, index, [Qt.CheckStateRole])
            return True

        return False

    def add_item(self, icon: QIcon, name: str, description: str = ""):
        self.beginInsertRows(QModelIndex(), 0, 0)
        self._data.append(
            {"checked": False, "icon": icon, "name": name, "description": description}
        )
        self.endInsertRows()

    def clear(self):
        self.beginResetModel()
        self._data.clear()
        self.endResetModel()

    def items(self):
        return self._data


class ChoiceView(QListView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._check_state = Qt.Checked

    def keyPressEvent(self, event: QKeyEvent):

        if self.model():
            if (
                event.key() == Qt.Key_Space
                and len(self.selectionModel().selectedRows()) > 1
            ):

                self._check_state = (
                    Qt.Checked if self._check_state == Qt.Unchecked else Qt.Unchecked
                )
                for row in self.selectionModel().selectedRows(0):
                    self.model().setData(row, self._check_state, Qt.CheckStateRole)
                    self.model().dataChanged.emit(row, row)

            else:
                super().keyPressEvent(event)


class ChoiceWidget(QWidget):
    visibility_changed = Signal()
    accepted = Signal()

    def __init__(self, parent=None):
        super().__init__()
        self._search_line = QLineEdit()
        self._listview = ChoiceView()
        self._model = ChoiceModel()
        self._proxy_model = QSortFilterProxyModel()
        self._proxy_model.setSourceModel(self._model)
        self._apply_btn = QPushButton(self.tr("Apply"))
        self._apply_btn.setFocusPolicy(Qt.NoFocus)
        self.set_placeholder(self.tr("Filter ..."))

        self._listview.setModel(self._proxy_model)
        self._listview.setSelectionMode(QAbstractItemView.ContiguousSelection)
        vlayout = QVBoxLayout(self)
        vlayout.addWidget(self._search_line)
        vlayout.addWidget(self._listview)
        vlayout.addWidget(self._apply_btn)

        self._search_line.textChanged.connect(self._proxy_model.setFilterFixedString)
        self._apply_btn.clicked.connect(self.__close_parent)

    def set_placeholder(self, message: str):
        self._search_line.setPlaceholderText(message)

    def clear(self):
        self._model.clear()

    def __close_parent(self):
        if self.parent():
            self.parent().close()

        self.accepted.emit()

    def add_item(self, icon: QIcon, name: str, description: str = ""):
        self._model.add_item(icon, name, description)

    def selected_items(self):
        result = []
        for i in self._model.items():
            if i["checked"] == True:
                result.append(i["name"])

        return result


def create_widget_action(toolbar: QToolBar, widget: QWidget):

    action = toolbar.addAction("menu")
    widget_action = QWidgetAction(toolbar)
    widget_action.setDefaultWidget(widget)
    menu = QMenu()
    action.setMenu(menu)
    widget.setParent(menu)
    menu.addAction(widget_action)
    toolbar.widgetForAction(action).setPopupMode(QToolButton.InstantPopup)

    return action


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)

    w = QMainWindow()

    m = QStringListModel()
    m.setStringList(["sacha", "boby", "truc"])
    wc = ChoiceWidget()
    wc.set_model(m)

    toolbar = w.addToolBar("test")

    create_widget_action(toolbar, wc)

    w.show()

    app.exec_()
