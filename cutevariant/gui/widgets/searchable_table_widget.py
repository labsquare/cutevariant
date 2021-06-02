from cutevariant.gui.ficon import FIcon
import typing

from PySide2.QtWidgets import (
    QAction,
    QTableView,
    QWidget,
    QAbstractItemView,
    QLineEdit,
    QVBoxLayout,
)
from PySide2.QtCore import (
    QModelIndex,
    QSortFilterProxyModel,
    QAbstractItemModel,
    Signal,
    Qt,
)
from PySide2.QtGui import QPainter

from cutevariant.commons import GENOTYPE_DESC


class LoadingTableView(QTableView):
    def __init__(self, parent=None):
        super().__init__(parent)

        self._is_loading = False

    def paintEvent(self, event: QPainter):

        if self._is_loading:
            painter = QPainter(self.viewport())

            painter.drawText(
                self.viewport().rect(), Qt.AlignCenter, self.tr("Loading ...")
            )

        else:
            super().paintEvent(event)

    def start_loading(self):
        self._is_loading = True
        self.viewport().update()

    def stop_loading(self):
        self._is_loading = False
        self.viewport().update()


class SearchableTableWidget(QWidget):
    """Convenient widget that displays a QTableView along with a search line edit.
    This class takes care of displaying a loading message when start_loading is called (and removes the message when stop_loading is called).
    """

    # Convenient signal to tell when current index changes. Returns index in **source** coordinates
    current_index_changed = Signal(QModelIndex)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.tableview = LoadingTableView(self)
        self.proxy = QSortFilterProxyModel(self)

        self.tableview.setModel(self.proxy)
        self.tableview.horizontalHeader().setStretchLastSection(True)
        self.tableview.setAlternatingRowColors(True)
        self.tableview.setSelectionMode(QAbstractItemView.ExtendedSelection)

        self.search_edit = QLineEdit(self)

        self.search_edit.textChanged.connect(self.proxy.setFilterRegExp)
        self.search_edit.setPlaceholderText(self.tr("Search..."))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.tableview)
        layout.addWidget(self.search_edit)

        self.tableview.verticalHeader().hide()

        self.tableview.selectionModel().currentChanged.connect(
            lambda cur, prev: self.current_index_changed.emit(cur)
        )

    def set_model(self, model: QAbstractItemModel):
        self.proxy.setSourceModel(model)

    def selected_indexes(self):
        if self.tableview.selectedIndexes():
            return [
                self.proxy.mapToSource(index)
                for index in self.tableview.selectedIndexes()
            ]
        else:
            return []

    def start_loading(self):
        self.search_edit.hide()
        self.tableview.start_loading()

    def stop_loading(self):
        self.tableview.stop_loading()
        self.search_edit.show()
