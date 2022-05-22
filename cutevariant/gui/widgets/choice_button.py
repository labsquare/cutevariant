import typing

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

from cutevariant.gui.ficon import FIcon


class ChoiceModel(QAbstractListModel):

    choice_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self._data = []
        self.rows_checked = set()

    def rowCount(self, parent=QModelIndex()):
        """override

        Args:
            parent (TYPE, optional): Description

        Returns:
            TYPE: Description
        """
        if parent == QModelIndex():
            return len(self._data)
        return 0

    def data(self, index: QModelIndex, role: Qt.ItemDataRole):
        """override

        Args:
            index (QModelIndex): Description
            role (Qt.ItemDataRole): Description

        Returns:
            TYPE: Description
        """
        if not index.isValid():
            return None

        if role == Qt.DisplayRole:
            text = self._data[index.row()]["name"]
            return text

        if role == Qt.DecorationRole:
            return QIcon(self._data[index.row()]["icon"])

        if role == Qt.CheckStateRole:
            return int(Qt.Checked) if self._data[index.row()]["checked"] else int(Qt.Unchecked)

        if role == Qt.ToolTipRole:
            return self._data[index.row()]["description"]

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        """override

        Args:
            index (QModelIndex): Description

        Returns:
            Qt.ItemFlags: Description
        """
        return Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsUserCheckable

    def setData(self, index: QModelIndex, value: typing.Any, role: Qt.ItemDataRole):
        """override

        Args:
            index (QModelIndex): Description
            value (TYPE): Description
            role (Qt.ItemDataRole): Description

        Returns:
            TYPE: Description
        """
        if role == Qt.CheckStateRole:

            checked = True if value == Qt.Checked else False
            self._data[index.row()]["checked"] = checked

            if checked:
                self.rows_checked.add(index.row())
            else:
                self.rows_checked.remove(index.row())

            self.dataChanged.emit(index, index, [Qt.CheckStateRole])
            self.choice_changed.emit()
            return True

        return False

    def add_item(self, icon: QIcon, name: str, description: str = "", data=None):
        """Add item

        Args:
            icon (QIcon): Description
            name (str): Description
            description (str, optional): Description
            data (None, optional): Description
        """
        self.beginInsertRows(QModelIndex(), 0, 0)
        self._data.append(
            {
                "checked": False,
                "icon": icon,
                "name": name,
                "description": description,
                "data": data,
            }
        )
        self.endInsertRows()
        self.choice_changed.emit()

    def clear(self):
        """Clear items"""
        self.beginResetModel()
        self._data.clear()
        self.rows_checked.clear()
        self.endResetModel()
        self.choice_changed.emit()

    def uncheck_all(self):
        """Uncheck all items"""
        self.beginResetModel()

        for i in self._data:
            i["checked"] = False

        self.rows_checked.clear()
        self.endResetModel()
        self.choice_changed.emit()

    def items(self):
        """Return all items"""
        return self._data

    def set_checked(self, names: typing.List[str]):
        """Set checked by names

        Args:
            names (typing.List[str]): Names of items
        """
        self.beginResetModel()

        for i in self._data:
            i["checked"] = False

        self.rows_checked.clear()

        for index, i in enumerate(self._data):
            if i["name"] in names:
                i["checked"] = True
                self.rows_checked.add(index)

        self.endResetModel()
        self.choice_changed.emit()

    def get_checked(self) -> typing.List[str]:
        return sorted([self._data[i]["name"] for i in self.rows_checked])


# class ChoiceView(QListView):
#     def __init__(self, parent=None):
#         super().__init__(parent)
#         self._check_state = Qt.Checked
#         self.setIconSize(QSize(16, 16))

# def keyPressEvent(self, event: QKeyEvent):

#     if self.model():
#         if event.key() == Qt.Key_Space and len(self.selectionModel().selectedRows()) > 1:

#             self._check_state = (
#                 Qt.Checked if self._check_state == Qt.Unchecked else Qt.Unchecked
#             )
#             for row in self.selectionModel().selectedRows(0):
#                 self.model().setData(row, self._check_state, Qt.CheckStateRole)
#                 self.model().dataChanged.emit(row, row)

#         else:
#             super().keyPressEvent(event)


class ChoiceButton(QPushButton):

    item_changed = Signal(list)

    def __init__(self, parent=None):
        super().__init__()

        self.prefix = "Status"
        self._model = ChoiceModel()
        self._proxy_model = QSortFilterProxyModel()
        self._proxy_model.setSourceModel(self._model)
        self.view = QListView()
        self.view.setModel(self._proxy_model)

        self.search_edit = QLineEdit()
        self.search_edit.textChanged.connect(self._proxy_model.setFilterWildcard)

        self.menu_widget = QMenu(self)
        self.widget_action = QWidgetAction(self)

        self.widget = QWidget()
        self.setFixedWidth(100)
        self.setFlat(True)

        vlayout = QVBoxLayout(self.widget)
        vlayout.addWidget(self.search_edit)
        vlayout.addWidget(self.view)

        self.widget_action.setDefaultWidget(self.widget)
        self.menu_widget.addAction(self.widget_action)

        self._model.choice_changed.connect(self._update_title)
        self.setMenu(self.menu_widget)

        self._update_title()

    def _update_title(self):
        checked = self._model.get_checked()
        names = ",".join(checked)

        if not names:
            names = "All"

        metrics = QFontMetrics(self.font())
        elidedText = metrics.elidedText(
            f"{self.prefix}: {names}", Qt.ElideMiddle, self.width() - 10
        )
        self.setText(f"{elidedText}")

        self.item_changed.emit(checked)

        # self.menu_widget.close()

    def clear(self):
        self._model.clear()

    def add_item(self, icon: QIcon, name: str, description: str = "", data: typing.Any = None):
        self._model.add_item(icon, name, description, data)

    def get_checked(self):
        return self._model.get_checked()

    def set_checked(self, names: typing.List[str]):
        self._model.set_checked(names)

    def clear(self):
        self._model.clear()

    def uncheck_all(self):
        self._model.uncheck_all()


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)

    w = QWidget()
    l = QVBoxLayout(w)
    btn = ChoiceButton()

    for i in range(100):
        btn.add_item(QIcon(), f"test {i}", "truc")

    l.addWidget(btn)

    btn.set_checked(["test2"])

    w.show()

    app.exec()
