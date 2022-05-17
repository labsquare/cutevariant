import sqlite3
from PySide6.QtWidgets import (
    QTabWidget,
    QTableView,
    QWidget,
    QDialog,
    QApplication,
    QLineEdit,
    QAbstractItemView,
    QSizePolicy,
    QVBoxLayout,
    QToolBar,
    QSplitter,
    QDialogButtonBox,
)
from PySide6.QtCore import (
    QAbstractTableModel,
    QModelIndex,
    Signal,
    Slot,
    QStringListModel,
    Qt,
    QSize,
)
from PySide6.QtGui import QAction, QIcon, QFont
from cutevariant import LOGGER

from cutevariant.core import sql
from cutevariant.gui.widgets import ChoiceButton


from cutevariant.config import Config
from cutevariant.gui.ficon import FIcon


class SamplesModel(QAbstractTableModel):
    def __init__(self, conn: sqlite3.Connection, parent=None):
        super().__init__(parent)
        self._data = []
        self._headers = ["name", "family", "Statut", "Tags"]
        self.query = ""
        self.conn = conn

    def rowCount(self, parent=QModelIndex()):
        """override"""
        if parent == QModelIndex():
            return len(self._data)
        return 0

    def columnCount(self, parent=QModelIndex()):
        """override"""
        if parent == QModelIndex():
            return len(self._headers)

        return 0

    def data(self, index: QModelIndex, role: Qt.ItemDataRole):

        if not index.isValid():
            return
        if role == Qt.DisplayRole:
            sample = self._data[index.row()]
            if index.column() == 0:
                return sample["name"]

            if index.column() == 1:
                return sample["family_id"]

            if index.column() == 2:
                return sample["classification"]

            if index.column() == 3:
                return sample["tags"]

        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role: Qt.ItemDataRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self._headers[section]

    def load(self):
        if self.conn:
            self.beginResetModel()
            try:
                self._data = list(sql.get_samples_from_query(self.conn, self.query))
            except:
                pass

            self.endResetModel()

    def get_sample(self, row: int):
        return self._data[row]


## Second Tab
class SelectionDialog(QDialog):

    selection_changed = Signal(int)

    def __init__(self, parent=None):
        super().__init__()

        self.toolbar = QToolBar()
        self.model = QStringListModel()
        self.view = QTableView()
        self.view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.view.horizontalHeader().hide()
        self.view.setShowGrid(False)
        self.view.verticalHeader().hide()
        self.view.horizontalHeader().setStretchLastSection(True)
        self.view.setModel(self.model)
        v_layout = QVBoxLayout(self)
        v_layout.addWidget(self.toolbar)

        v_layout.addWidget(self.view)
        self._setup_actions()

        self.setWindowTitle(self.tr("Selected sample(s)"))

    def _setup_actions(self):
        sep = QWidget()
        sep.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.toolbar.addAction(QIcon(), "Remove selection(s)", self._on_remove)
        self.toolbar.addWidget(sep)
        self.toolbar.addAction(QIcon(), "Clear all", self._on_clear)

    def set_samples(self, samples):
        previous = set(self.model.stringList())

        samples = set(samples).union(previous)

        self.model.setStringList(samples)
        self.selection_changed.emit(self.model.rowCount())

    def get_samples(self):
        return self.model.stringList()

    def _on_remove(self):
        names = self.model.stringList()

        for index in self.view.selectionModel().selectedRows():
            del names[index.row()]

        self.model.setStringList(names)
        self.selection_changed.emit(self.model.rowCount())

    def _on_clear(self):
        self.model.setStringList([])
        self.selection_changed.emit(self.model.rowCount())


class SamplesWidget(QWidget):
    def __init__(self, conn: sqlite3.Connection, parent=None):
        super().__init__()

        self.toolbar = QToolBar()
        self.line = QLineEdit()
        self.line.setPlaceholderText("Search sample ...")
        self.line.textChanged.connect(self._on_search)

        self.model = SamplesModel(conn)

        self.selection_dialog = SelectionDialog()
        self.selection_dialog.selection_changed.connect(self._update_count)

        self.view = QTableView()
        self.view.verticalHeader().hide()
        self.view.horizontalHeader().setStretchLastSection(True)
        self.view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.view.setSelectionMode(QAbstractItemView.ContiguousSelection)
        self.view.setModel(self.model)

        v_layout = QVBoxLayout(self)
        v_layout.addWidget(self.toolbar)
        v_layout.addWidget(self.line)
        v_layout.addWidget(self.view)

        self._setup_actions()

        self.view.doubleClicked.connect(self._on_add_selection)

        # TODO : CHARGER QD ON OUVRE LE WIDGET
        config = Config("classifications")
        self.CLASSIFICATION = config.get("samples")

        self.conn = None

    def get_selected_samples(self):
        return self.selection_dialog.get_samples()

    def set_selected_samples(self, samples: list):
        self.selection_dialog.set_samples(samples)

    def _setup_actions(self):

        # Filters
        self.family_choice = ChoiceButton()
        self.family_choice.item_changed.connect(self._on_filter_changed)
        self.family_choice.prefix = self.tr("Familly")
        self.statut_choice = ChoiceButton()
        self.statut_choice.item_changed.connect(self._on_filter_changed)
        self.statut_choice.prefix = self.tr("Status")
        self.tag_choice = ChoiceButton()
        self.tag_choice.item_changed.connect(self._on_filter_changed)
        self.tag_choice.prefix = self.tr("Tag")

        self.toolbar.addWidget(self.family_choice)
        self.toolbar.addWidget(self.statut_choice)
        self.toolbar.addWidget(self.tag_choice)

        self.toolbar.addSeparator()
        clear_action = self.toolbar.addAction(QIcon(), "Clear filters", self.clear_filters)

        # separator
        sep = QWidget()
        sep.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.toolbar.addWidget(sep)
        self.add_button = self.toolbar.addAction("Add To Selection")
        self.add_button.setIcon(FIcon(0xF0415))
        self.add_button.setToolTip(self.tr("Add selections to basket"))
        self.add_button.triggered.connect(self._on_add_selection)
        self.basket_button = self.toolbar.addAction("Selected samples")
        self.basket_button.setToolTip(self.tr("Show selected samples"))
        self.basket_button.setIcon(FIcon(0xF0076))
        self.basket_button.triggered.connect(self._on_basket_clicked)
        # self.toolbar.widgetForAction(self.basket_button).setAutoRaise(False)

        self.toolbar.setIconSize(QSize(16, 16))
        self.toolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)

    def _load_filters(self):
        if self.conn:
            # Load family
            self.family_choice.clear()
            for fam in sql.get_samples_family(self.conn):
                self.family_choice.add_item(QIcon(), fam, data=fam)

            # Load Status
            self.statut_choice.clear()
            for item in self.CLASSIFICATION:
                self.statut_choice.add_item(QIcon(), item["name"], data=item["number"])

            # Load Tags
            self.tag_choice.clear()
            tags = sql.get_tags_from_samples(self.conn)
            for tag in tags:
                self.tag_choice.add_item(QIcon(), tag, data=tag)

    def clear_filters(self):
        self.tag_choice.uncheck_all()
        self.family_choice.uncheck_all()
        self.statut_choice.uncheck_all()
        self._on_search()

    def _on_filter_changed(self):
        tag_list = self.tag_choice._model.get_checked()
        fam_list = self.family_choice._model.get_checked()
        class_list = [str(i["data"]) for i in self.statut_choice._model.items() if i["checked"]]

        query = []
        if tag_list:
            query += ["tags:" + ",".join(tag_list)]

        if fam_list:
            query += ["family:" + ",".join(fam_list)]

        if class_list:
            query += ["classification:" + ",".join(class_list)]

        query = " ".join(query)

        if not self.line.text():
            self.line.setText(query)
        else:
            self.line.setText(self.line.text() + " " + query)

    def _on_search(self):
        """Start a search query"""
        self.model.query = self.line.text()
        self.model.load()

    def _on_add_selection(self):

        samples = [
            self.model.get_sample(i.row())["name"]
            for i in self.view.selectionModel().selectedRows()
        ]

        self.selection_dialog.set_samples(samples)

    def _update_count(self):
        count = len(self.selection_dialog.get_samples())
        self.basket_button.setText(f"{count} Selected sample(s)")
        font = self.basket_button.font()
        font.setBold(count > 0)
        self.basket_button.setFont(font)
        # font = QFont()
        # font.setBold(count > 0)
        # self.basket_button.setFont(font)

    @property
    def conn(self):
        return self.model.conn

    @conn.setter
    def conn(self, conn):
        self.model.conn = conn
        self.model.load()
        self._load_filters()

    def _on_basket_clicked(self):

        self.selection_dialog.exec()


class SamplesDialog(QDialog):
    def __init__(self, conn, parent=None):
        super().__init__(parent)

        self.w = SamplesWidget(conn)
        self.w.conn = conn

        self.btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.btn_box.accepted.connect(self.accept)
        self.btn_box.rejected.connect(self.reject)

        self.btn_box.buttons()[0].setFlat(False)

        v_layout = QVBoxLayout(self)
        v_layout.addWidget(self.w)
        v_layout.addWidget(self.btn_box)
        self.resize(800, 400)

        self.setWindowTitle(self.tr("Select sample(s)"))

    def set_samples(self, samples: list):
        self.w.set_selected_samples(samples)

    def get_samples(self):
        return self.w.get_selected_samples()


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)

    conn = sql.get_sql_connection("/home/sacha/test.db")

    w = SamplesDialog(conn)
    w.set_samples(["Sample1"])
    w.exec()

    print(w.get_samples())

    app.exec()
