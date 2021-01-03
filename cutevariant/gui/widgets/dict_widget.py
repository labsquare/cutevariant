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
from PySide2.QtGui import (
    QFont,
    QContextMenuEvent,
    QColor,
    QKeySequence,
    QPaintEvent,
    QPainter,
)


class DictModel(QAbstractTableModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._raw_data = []
        self._headers = ["Key", "Value"]

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 2

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self._raw_data)

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:

        if index.column() == 0:
            return Qt.ItemIsSelectable | Qt.ItemIsEnabled

        if index.column() == 1:
            return Qt.ItemIsSelectable | Qt.ItemIsEnabled

    def data(self, index: QModelIndex, role: Qt.ItemDataRole = Qt.DisplayRole):

        if not index.isValid():
            return None

        if role == Qt.DisplayRole or role == Qt.ToolTipRole:
            return self.value(index)

        if role == Qt.FontRole:
            value = self.value(index)
            font = QFont()
            if index.column() == 0:
                font.setBold(True)
            if index.column() == 1 and value == "NULL":
                font.setItalic(True)
            return font

        if role == Qt.TextColorRole:
            value = self.value(index)
            if index.column() == 1 and value == "NULL":
                return QColor("lightgray")

        return None

    def value(self, index: QModelIndex):
        if index.isValid():
            value = self._raw_data[index.row()][index.column()]
            if value is None:
                return "NULL"
            else:
                return value
        else:
            return None

    def headerData(
        self, section: int, orientation: Qt.Orientation, role: Qt.ItemDataRole
    ):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self._headers[section]

        return None

    def set_dict(self, data: dict):

        if data:
            self.beginResetModel()
            self._raw_data = [(k, v) for k, v in data.items()]
            self.endResetModel()

    def clear(self):
        self.set_dict({})


class DictWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__()

        self.view = QTableView()
        self.model = DictModel()
        self.proxy_model = QSortFilterProxyModel()
        self.search_bar = QLineEdit()
        self._show_loading = False

        self.proxy_model.setSourceModel(self.model)

        self.view.setModel(self.proxy_model)
        self.view.setAlternatingRowColors(True)
        self.view.horizontalHeader().setStretchLastSection(True)
        self.view.setSelectionMode(QAbstractItemView.SingleSelection)
        self.view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.view.setSortingEnabled(True)
        self.view.verticalHeader().hide()

        self.search_bar.textChanged.connect(self.proxy_model.setFilterRegularExpression)
        self.search_bar.setVisible(False)

        self._show_search_action = QAction("show search bar")
        self._show_search_action.setCheckable(True)
        self._show_search_action.setShortcutContext(Qt.WidgetShortcut)
        self._show_search_action.setShortcut(QKeySequence.Find)
        self._show_search_action.triggered.connect(self._on_show_search)

        self._close_search_action = QAction()
        self._close_search_action.setShortcut(QKeySequence(Qt.Key_Escape))
        self._close_search_action.setShortcutContext(Qt.WidgetShortcut)
        self._close_search_action.triggered.connect(self._on_close_search)

        self.view.addAction(self._show_search_action)
        self.search_bar.addAction(self._close_search_action)

        _layout = QVBoxLayout()
        _layout.addWidget(self.view)
        _layout.addWidget(self.search_bar)
        _layout.setContentsMargins(0, 0, 0, 0)

        self.setLayout(_layout)
        print("init")

    def set_dict(self, data: dict):

        self.model.set_dict(data)

    def _on_show_search(self):
        self.search_bar.setVisible(True)
        self.search_bar.setFocus(Qt.ShortcutFocusReason)

    def _on_close_search(self):
        self.search_bar.hide()
        self.search_bar.clear()
        self.view.setFocus(Qt.ShortcutFocusReason)

    def set_header_visible(self, visible=True):
        self.view.horizontalHeader().setVisible(visible)

    def clear(self):
        self.model.clear()

    def paintEvent(self, event: QPaintEvent):

        if self._show_loading:
            painter = QPainter(self)
            painter.drawText(self.rect(), Qt.AlignCenter, self.tr("Loading ..."))
        else:
            super().paintEvent(event)

    def set_loading(self, show=True):
        self._show_loading = True
        self.view.setVisible(not show)
        self.update()


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)

    w = DictWidget()
    w.set_dict({"name": "sacha", "age": 13, "sexe": True})

    w.show()
    app.exec_()
