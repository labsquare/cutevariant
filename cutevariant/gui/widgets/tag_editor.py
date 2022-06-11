from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
import typing

from cutevariant.gui.ficon import FIcon

# Tags {
#     "name":"tags name",
#     "color":"color",
#     "description": "sdfsdf"
# }

LOCKED_SECTION = ["samples"]


class TagDialog(QDialog):
    def __init__(self, section=None):
        super().__init__()

        self.section = section

        # self.number_edit = QLineEdit()
        # self.number_edit.setPlaceholderText("Tag id")
        # self.number_edit.setValidator(QIntValidator())
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Tag Name ...")
        # self.lock_edit = QCheckBox(self.tr("Locked Tag"))
        self.color_edit = QPushButton()
        self.descr_edit = QTextEdit()
        self.descr_edit.setPlaceholderText("Description ...")

        self.btn_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)

        form_layout = QVBoxLayout()
        # form_layout.addWidget(self.number_edit)
        form_layout.addWidget(self.name_edit)
        # if self.section in LOCKED_SECTION:
        #     form_layout.addWidget(self.lock_edit)
        form_layout.addWidget(self.color_edit)

        v_layout = QVBoxLayout(self)
        v_layout.addLayout(form_layout)
        v_layout.addWidget(self.descr_edit)
        v_layout.addWidget(self.btn_box)

        self.color_edit.clicked.connect(self._on_select_color)

        self._set_color("#B7B7B8")

        self.btn_box.rejected.connect(self.reject)
        self.btn_box.accepted.connect(self.accept)

    def set_tag(self, tag: dict):

        # self.number_edit.setText(str(tag.get("number", 0)))
        self.name_edit.setText(str(tag.get("name", "")))
        # self.lock_edit.setChecked(bool(tag.get("lock", False)))
        self.descr_edit.setPlainText(str(tag.get("description", "")))
        self._set_color(tag.get("color", "black"))

    def get_tag(self) -> dict:

        tag = {}
        # tag["number"] = int(self.number_edit.text())
        tag["name"] = self.name_edit.text()
        # tag["lock"] = self.lock_edit.isChecked() or False
        tag["description"] = self.descr_edit.toPlainText()
        tag["color"] = self.color_edit.text()
        return tag

    def _on_select_color(self):
        color = QColorDialog.getColor()

        if color:
            self._set_color(color)

    def _set_color(self, color: str):
        pix = QPixmap(64, 64)
        pix.fill(QColor(color))
        self.color_edit.setIcon(QIcon(pix))
        self.color_edit.setText(QColor(color).name())


class TagDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex):

        # if index.column() == 0:

        #     text = str(index.data(Qt.DisplayRole))
        #     color = index.model().tag(index)["color"]
        #     metrics = QFontMetrics(painter.font())
        #     rect = metrics.boundingRect(text)
        #     rect.moveCenter(option.rect.center())
        #     rect = rect.adjusted(-3, -3, 3, 3)
        #     painter.setBrush(QBrush(color))
        #     painter.setPen(Qt.NoPen)
        #     painter.drawRoundedRect(rect, 2, 2)
        #     painter.setPen(QPen("white"))
        #     painter.drawText(rect, Qt.AlignCenter, text)

        #        else:
        return super().paint(painter, option, index)


class TagModel(QAbstractTableModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._data = []
        # self._headers = ["Number", "Name"]
        self._headers = ["Name", "Description"]

    def rowCount(self, parent=QModelIndex()):
        if parent == QModelIndex():
            return len(self._data)
        return 0

    def columnCount(self, parent=QModelIndex()):
        if parent == QModelIndex():
            return 2
        return 0

    def data(self, index: QModelIndex, role: Qt.ItemDataRole):

        if not index.isValid():
            return None

        if role == Qt.DisplayRole:
            if index.column() == 0:
                return self._data[index.row()]["name"]

            elif index.column() == 1:
                return self._data[index.row()]["description"]

        if role == Qt.DecorationRole and index.column() == 0:
            return QIcon(FIcon(0xF04F9, self._data[index.row()]["color"]))

        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role: Qt.ItemDataRole):

        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self._headers[section]

    def set_tags(self, tags: list):

        self.beginResetModel()
        self._data = tags
        self.endResetModel()

    def tag(self, index: QModelIndex):
        return self._data[index.row()]

    def get_tags(self):
        return self._data

    def add_tag(self, tag: dict):

        self.beginInsertRows(QModelIndex(), 0, 0)
        self._data.insert(0, tag)
        self.endInsertRows()

    def edit_tag(self, row: int, tag: dict):

        self._data[row] = tag
        self.dataChanged.emit(self.index(row, 0), self.index(row, 1))

    def remove_tags(self, rows: tuple):

        self.beginResetModel()
        for i in sorted(rows, reverse=True):
            del self._data[i]

        self.endResetModel()


class TagEditor(QWidget):

    COLOR_ROLE = Qt.UserRole
    DESCRIPTION_ROLE = Qt.UserRole + 1
    # NUMBER_ROLE = Qt.UserRole + 2

    def __init__(self, section=None):
        super().__init__()

        self.model = TagModel()

        self.delegate = TagDelegate()

        self.section = section

        self.view = QTableView()
        self.view.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.view.setModel(self.model)
        self.view.setItemDelegate(self.delegate)
        self.view.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.view.setShowGrid(False)
        self.view.horizontalHeader().setStretchLastSection(True)
        self.view.horizontalHeader().hide()
        self.view.setAlternatingRowColors(True)
        self.view.verticalHeader().hide()
        # self.view.selectionModel().selectionChanged.connect(self._on_selection_changed)

        self.add_button = QPushButton("Add")
        self.add_button.clicked.connect(self._on_add_tag)
        self.edit_button = QPushButton("Edit")
        self.edit_button.clicked.connect(self._on_edit_tag)
        self.rem_button = QPushButton("Delete")
        self.rem_button.clicked.connect(self._on_rem_tag)

        # Create button layout
        btn_layout = QVBoxLayout()
        btn_layout.addWidget(self.add_button)
        btn_layout.addWidget(self.edit_button)
        btn_layout.addStretch()
        btn_layout.addWidget(self.rem_button)

        # Create main layout
        main_layout = QHBoxLayout(self)
        main_layout.addWidget(self.view)
        main_layout.addLayout(btn_layout)

        # self._items = []

    def _on_add_tag(self):

        dialog = TagDialog(section=self.section)
        if dialog.exec() == QDialog.Accepted:
            tag = dialog.get_tag()
            self.model.add_tag(tag)

    def _on_edit_tag(self):

        current_index = self.view.selectionModel().currentIndex()
        tag = self.model.tag(current_index)

        dialog = TagDialog(section=self.section)
        dialog.set_tag(tag)
        if dialog.exec() == QDialog.Accepted:
            tag = dialog.get_tag()
            self.model.edit_tag(current_index.row(), tag)

    def _on_rem_tag(self):

        indexes = self.view.selectionModel().selectedIndexes()
        rows = {index.row() for index in indexes}
        self.model.remove_tags(rows)

    def set_tags(self, tags: typing.List[dict]):
        self.model.set_tags(tags)
        self.view.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)

    def get_tags(self):
        return self.model.get_tags()


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)

    w = TagEditor()

    w.set_tags(
        [
            {"name": "Pathogene", "color": "red", "description": "test"},
            {
                "name": "Likly Pathogene",
                "color": "orange",
                "description": "test",
            },
            {"name": "Benin", "color": "purple", "description": "test"},
            {"name": "boby", "color": "orange", "description": "test"},
        ]
    )

    w.show()

    app.exec()
