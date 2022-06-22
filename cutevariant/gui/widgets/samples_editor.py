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

    """A Model showing sqlite samples

    Attributes:
        conn (sqlite.Connection)
        query (str): Samples filters

    Examples:
        model = SampleEditorModel(conn)
        model.query = "boby status:3 classification:4"
        model.load()


    """

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

    def data(self, index: QModelIndex, role: Qt.ItemDataRole) -> typing.Any:
        """override"""
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
        """override"""
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self._headers[section]

    def load(self):
        """Load samples from sqlite"""
        if self.conn:
            self.beginResetModel()
            self._data = list(sql.get_samples_from_query(self.conn, self.query))

            self.endResetModel()

    def get_sample(self, row: int) -> dict:
        """Get all sample from row"""
        return self._data[row]


class SamplesEditor(QDialog):

    """A Widget to select samples from the databases"""

    sample_selected = Signal(list)

    def __init__(self, conn: sqlite3.Connection = None, parent=None):
        super().__init__()

        # Create model
        self.model = SamplesEditorModel(conn)

        # Create view
        self.view = QTableView()
        self.view.verticalHeader().hide()
        self.view.horizontalHeader().setStretchLastSection(True)
        self.view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.view.setSelectionMode(QAbstractItemView.MultiSelection)
        self.view.setModel(self.model)
        self.view.selectionModel().selectionChanged.connect(self.on_selectionChanged)

        # Create buttons box
        self.btn_box = QDialogButtonBox()
        self.btn_box.accepted.connect(self._on_accept)
        self.btn_box.rejected.connect(self.close)
        self.add_btn = self.btn_box.addButton("Add selection", QDialogButtonBox.AcceptRole)
        self.clear_btn = self.btn_box.addButton("Clear selection", QDialogButtonBox.ResetRole)
        self.clear_btn.clicked.connect(self.view.selectionModel().clear)
        self.btn_box.addButton("Close", QDialogButtonBox.RejectRole)

        self.setWindowTitle(self.tr("Select sample(s)"))

        # Create toolbar
        self.toolbar = QToolBar()
        self.line = QLineEdit()
        self.line.setPlaceholderText("Search sample ...")
        self.line.textChanged.connect(self._on_search)

        # Create layout
        v_layout = QVBoxLayout(self)
        v_layout.addWidget(self.toolbar)
        v_layout.addWidget(self.line)
        v_layout.addWidget(self.view)
        v_layout.addWidget(self.btn_box)

        self._setup_actions()

        config = Config("classifications")
        self.CLASSIFICATION = config.get("samples")

        self.conn = conn
        self.on_selectionChanged()

    def load(self):
        """Load samples"""
        self.model.load()

    def on_selectionChanged(self):

        count = len(self.view.selectionModel().selectedRows())
        self.add_btn.setEnabled(count > 0)
        if count > 0:
            self.add_btn.setText(f"Add {count} samples(s) ")

        else:
            self.add_btn.setText(f"Add samples(s) ")

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
            tags_list = []
            for tag in tags:
                tag_list = tag.split(",")
                for t in tag_list:
                    if t not in tags_list:
                        tags_list.append(t)
            for tag in tags_list:
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
        class_list = [str(i["data"]) for i in self.statut_choice._model.items() if i["checked"]]

        # clean previous query line
        previous_query_line_list = []
        previous_query_line_text = self.line.text()
        before_query_line_list = []
        if previous_query_line_text:
            previous_query_line_list = previous_query_line_text.split(" ")
            for q in previous_query_line_list:
                if (
                    not q.startswith("tags:")
                    and not q.startswith("classification:")
                    and not q.startswith("family_id:")
                    and not q == ""
                ):
                    before_query_line_list.append(q)

        if before_query_line_list:
            previous_query_line_text_clean = " ".join(before_query_line_list)
        else:
            previous_query_line_text_clean = ""

        # start query
        query = []

        # tag
        if tag_list:
            for tag in tag_list:
                query += ["tags:" + tag]

        # family
        if fam_list:
            query += ["family_id:" + ",".join(fam_list)]

        # classification
        if class_list:
            query += ["classification:" + ",".join(class_list)]

        # construct query
        query = " ".join(query)

        # change query
        if not self.line.text():
            # if not previous_query_line_text_clean:
            self.line.setText(query)
        else:
            # self.line.setText(self.line.text() + " " + query)
            self.line.setText(previous_query_line_text_clean + " " + query)

    def _on_search(self):
        """Start a search query"""
        self.model.query = self.line.text().strip()
        self.model.load()

    def get_selected_samples(self) -> typing.List[str]:
        """Return selected samples"""
        samples = []
        for index in self.view.selectionModel().selectedRows():
            samples.append(self.model.get_sample(index.row())["name"])

        return samples

    def _on_accept(self):
        self.sample_selected.emit(self.get_selected_samples())
        self.accept()

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
    from cutevariant.commons import create_fake_conn

    app = QApplication(sys.argv)

    w = SamplesEditor(create_fake_conn())
    w.exec()
