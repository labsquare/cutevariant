import sqlite3
import typing
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


class SamplesEditorModel(QAbstractTableModel):
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

    def headerData(
        self, section: int, orientation: Qt.Orientation, role: Qt.ItemDataRole
    ):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self._headers[section]

    def load(self):
        if self.conn:
            self.beginResetModel()
            self._data = list(sql.get_samples_from_query(self.conn, self.query))

            self.endResetModel()

    def get_sample(self, row: int):
        return self._data[row]


class SamplesEditor(QWidget):

    sample_selected = Signal(list)

    def __init__(self, conn: sqlite3.Connection = None, parent=None):
        super().__init__()

        self.btn_box = QDialogButtonBox()
        self.btn_box.addButton("Add selection", QDialogButtonBox.AcceptRole)
        self.btn_box.addButton("Close", QDialogButtonBox.RejectRole)
        self.btn_box.accepted.connect(self._on_accept)
        self.btn_box.rejected.connect(self.close)

        self.setWindowTitle(self.tr("Select sample(s)"))

        self.toolbar = QToolBar()
        self.line = QLineEdit()
        self.line.setPlaceholderText("Search sample ...")
        self.line.textChanged.connect(self._on_search)

        self.model = SamplesEditorModel(conn)

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
        v_layout.addWidget(self.btn_box)

        self._setup_actions()

        self.view.doubleClicked.connect(self._on_accept)

        # TODO : CHARGER QD ON OUVRE LE WIDGET
        config = Config("classifications")
        self.CLASSIFICATION = config.get("samples")

        self.conn = conn

    def load(self):
        self.model.load()

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
        clear_action = self.toolbar.addAction(
            QIcon(), "Clear filters", self.clear_filters
        )

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
        self.line.clear()
        self._on_search()

    def _on_filter_changed(self):
        tag_list = self.tag_choice._model.get_checked()
        fam_list = self.family_choice._model.get_checked()
        class_list = [
            str(i["data"]) for i in self.statut_choice._model.items() if i["checked"]
        ]

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

    def get_selected_samples(self) -> typing.List[str]:
        """Return selected samples"""
        samples = []
        for index in self.view.selectionModel().selectedRows():
            samples.append(self.model.get_sample(index.row())["name"])

        return samples

    def _on_accept(self):
        self.sample_selected.emit(self.get_selected_samples())

    @property
    def conn(self):
        return self.model.conn

    @conn.setter
    def conn(self, conn):
        self.model.conn = conn
        self.model.load()
        self._load_filters()


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)

    conn = sql.get_sql_connection("/home/sacha/test.db")

    w = SamplesEditor(conn)
    w.show()

    app.exec()
