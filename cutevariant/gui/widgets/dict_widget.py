from PySide2.QtWidgets import (
    QTableView,
    QAbstractItemView,
    QApplication,
    QWidget,
    QVBoxLayout,
    QLineEdit,
    QMenu,
    QAction,
)
from PySide2.QtCore import QAbstractTableModel, QModelIndex, QSortFilterProxyModel, Qt
from PySide2.QtGui import QFont, QContextMenuEvent


class DictModel(QAbstractTableModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._raw_data = {}
        self._headers = ["Key", "Value"]

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 2

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self._raw_data)

    def data(self, index: QModelIndex, role: Qt.ItemDataRole = Qt.DisplayRole):

        if not index.isValid():
            return None

        if role == Qt.DisplayRole or role == Qt.ToolTipRole:
            return self._raw_data[index.row()][index.column()]

        if role == Qt.FontRole:
            if index.column() == 0:
                font = QFont()
                font.setBold(True)
                return font
        return None

    def headerData(
        self, section: int, orientation: Qt.Orientation, role: Qt.ItemDataRole
    ):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self._headers[section]

        return None

    def set_dict(self, data: dict):

        self.beginResetModel()
        self._raw_data = [(k, v) for k, v in data.items()]
        self.endResetModel()


class DictWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__()

        self.view = QTableView()
        self.model = DictModel()
        self.proxy_model = QSortFilterProxyModel()
        self.search_bar = QLineEdit()

        self.proxy_model.setSourceModel(self.model)

        self.view.setModel(self.proxy_model)
        self.view.setAlternatingRowColors(True)
        self.view.horizontalHeader().setStretchLastSection(True)
        self.view.setSelectionMode(QAbstractItemView.SingleSelection)
        self.view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.view.setSortingEnabled(True)

        self.search_bar.textChanged.connect(self.proxy_model.setFilterRegularExpression)
        self.search_bar.setVisible(False)
        self._show_search_action = QAction("show search bar")
        self._show_search_action.setCheckable(True)
        self._show_search_action.setShortcut(Qt.CTRL + Qt.Key_F)
        self._show_search_action.triggered.connect(lambda x: self._on_show_search(x))

        self.addAction(self._show_search_action)

        _layout = QVBoxLayout()
        _layout.addWidget(self.view)
        _layout.addWidget(self.search_bar)
        _layout.setContentsMargins(0, 0, 0, 0)

        self.setLayout(_layout)
        print("init")

    def set_dict(self, data: dict):

        self.model.set_dict(data)

    def _on_show_search(self, visible=True):
        print("show")
        self.search_bar.setVisible(visible)
        self.search_bar.setFocus(Qt.ShortcutFocusReason)


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)

    w = DictWidget()
    w.show()
    w.set_dict({"name": "sacha", "age": 13, "sexe": True})

    app.exec_()
