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


class ClassificationDialog(QDialog):
    def __init__(self, section=None):
        super().__init__()

        self.section = section

        self.number_edit = QLineEdit()
        self.number_edit.setPlaceholderText("Classification id")
        self.number_edit.setValidator(QIntValidator())
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Classification Name ...")
        self.lock_edit = QCheckBox(self.tr("Locked Classification"))
        self.color_edit = QPushButton()
        self.descr_edit = QTextEdit()
        self.descr_edit.setPlaceholderText("Description ...")

        self.btn_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)

        form_layout = QVBoxLayout()
        form_layout.addWidget(self.number_edit)
        form_layout.addWidget(self.name_edit)
        if self.section in LOCKED_SECTION:
            form_layout.addWidget(self.lock_edit)
        form_layout.addWidget(self.color_edit)

        v_layout = QVBoxLayout(self)
        v_layout.addLayout(form_layout)
        v_layout.addWidget(self.descr_edit)
        v_layout.addWidget(self.btn_box)

        self.color_edit.clicked.connect(self._on_select_color)

        self._set_color("#B7B7B8")

        self.btn_box.rejected.connect(self.reject)
        self.btn_box.accepted.connect(self.accept)

    def set_classification(self, classification: dict):

        self.number_edit.setText(str(classification.get("number", 0)))
        self.name_edit.setText(str(classification.get("name", "")))
        self.lock_edit.setChecked(bool(classification.get("lock", False)))
        self.descr_edit.setPlainText(str(classification.get("description", "")))
        self._set_color(classification.get("color", "black"))

    def get_classification(self) -> dict:

        classification = {}
        classification["number"] = int(self.number_edit.text())
        classification["name"] = self.name_edit.text()
        classification["lock"] = self.lock_edit.isChecked() or False
        classification["description"] = self.descr_edit.toPlainText()
        classification["color"] = self.color_edit.text()
        return classification

    def _on_select_color(self):

        color = QColorDialog.getColor()

        if color:
            self._set_color(color)

    def _set_color(self, color: str):
        pix = QPixmap(64, 64)
        pix.fill(QColor(color))
        self.color_edit.setIcon(QIcon(pix))
        self.color_edit.setText(QColor(color).name())


class ClassificationDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex):

        # if index.column() == 0:

        #     text = str(index.data(Qt.DisplayRole))
        #     color = index.model().classification(index)["color"]
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


class ClassificationModel(QAbstractTableModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._data = []
        self._headers = ["Number", "Name"]

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
            if index.column() == 1:
                return self._data[index.row()]["name"]

            if index.column() == 0:
                return self._data[index.row()]["number"]

        if role == Qt.DecorationRole and index.column() == 0:
            return QIcon(FIcon(0xF012F, self._data[index.row()]["color"]))

        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role: Qt.ItemDataRole):

        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self._headers[section]

    def set_classifications(self, classifications: list):

        self.beginResetModel()
        self._data = classifications
        self.endResetModel()

    def classification(self, index: QModelIndex):
        return self._data[index.row()]

    def get_classifications(self):
        return self._data

    def add_classification(self, classification: dict):

        self.beginInsertRows(QModelIndex(), 0, 0)
        self._data.insert(0, classification)
        self.endInsertRows()

    def edit_classification(self, row: int, classification: dict):

        self._data[row] = classification
        self.dataChanged.emit(self.index(row, 0), self.index(row, 1))

    def remove_classifications(self, rows: tuple):

        self.beginResetModel()
        for i in sorted(rows, reverse=True):
            del self._data[i]

        self.endResetModel()


class ClassificationEditor(QWidget):

    COLOR_ROLE = Qt.UserRole
    DESCRIPTION_ROLE = Qt.UserRole + 1
    NUMBER_ROLE = Qt.UserRole + 2

    def __init__(self, section=None):
        super().__init__()

        self.model = ClassificationModel()

        self.delegate = ClassificationDelegate()

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
        self.add_button.clicked.connect(self._on_add_classification)
        self.edit_button = QPushButton("Edit")
        self.edit_button.clicked.connect(self._on_edit_classification)
        self.rem_button = QPushButton("Delete")
        self.rem_button.clicked.connect(self._on_rem_classification)

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

    def _on_add_classification(self):

        dialog = ClassificationDialog(section=self.section)
        if dialog.exec() == QDialog.Accepted:
            classification = dialog.get_classification()
            self.model.add_classification(classification)

    def _on_edit_classification(self):

        current_index = self.view.selectionModel().currentIndex()
        classification = self.model.classification(current_index)

        dialog = ClassificationDialog(section=self.section)
        dialog.set_classification(classification)
        if dialog.exec() == QDialog.Accepted:
            classification = dialog.get_classification()
            self.model.edit_classification(current_index.row(), classification)

    def _on_rem_classification(self):

        indexes = self.view.selectionModel().selectedIndexes()
        rows = {index.row() for index in indexes}
        self.model.remove_classifications(rows)

    def set_classifications(self, classifications: typing.List[dict]):
        self.model.set_classifications(classifications)
        self.view.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)

    def get_classifications(self):
        return self.model.get_classifications()


#     def set_tags(self, tags: typing.List[dict]):
#         """Set tags
#         Args:
#             items (dict): {"name":"tag", color:"red", description: "a description"}
#         """
#         for tag in tags:
#             item = self._tag_to_item(tag)
#             self.view.addItem(item)

#     def get_tags(self) -> typing.List[dict]:
#         """Return dict"""

#         tags = []
#         for row in range(self.view.count()):
#             tags.append(self._item_to_tag(self.view.item(row)))

#         return tags

#     def add_tag(self, tag: dict):
#         self.view.addItem(self._tag_to_item(tag))

#     def edit_tag(self, tag: dict, row: int):

#         old_item = self.view.takeItem(row)
#         new_item = self._tag_to_item(tag)
#         self.view.insertItem(row, new_item)
#         del old_item

#     def _on_selection_changed(self):
#         select_count = len(self.view.selectionModel().selectedRows())

#         self.edit_button.setDisabled(select_count > 1)

#     def _item_to_tag(self, item: QListWidgetItem) -> dict:

#         tag = dict()
#         tag["name"] = item.text()

#         tag["color"] = item.data(TagEditor.COLOR_ROLE)
#         tag["description"] = item.data(TagEditor.DESCRIPTION_ROLE)

#         return tag

#     def _tag_to_item(self, tag: dict) -> QListWidgetItem:

#         item = QListWidgetItem()
#         item.setText(tag.get("name", "Unknown"))
#         item.setData(TagEditor.COLOR_ROLE, tag.get("color", "gray"))
#         item.setData(TagEditor.DESCRIPTION_ROLE, tag.get("description", ""))

#         pix = QPixmap(64, 64)
#         pix.fill(QColor(item.data(TagEditor.COLOR_ROLE)))

#         item.setIcon(QIcon(pix))

#         return item

#     def _on_add_tag(self):

#         dialog = TagDialog(self)
#         if dialog.exec() == QDialog.Accepted:

#             # Check if tag not exists
#             tag = dialog.get_tag()
#             existing_tags_names = [t["name"] for t in self.get_tags()]

#             if tag["name"] in existing_tags_names:
#                 name = tag["name"]
#                 ret = QMessageBox.warning(
#                     self,
#                     f"tag already exists",
#                     f"Do you want to overwrite tag `{name}` ?",
#                     QMessageBox.Yes | QMessageBox.No,
#                 )

#                 if ret == QMessageBox.Yes:
#                     items = self.view.findItems(name, Qt.MatchExactly)
#                     if items:
#                         row = self.view.row(items[0])
#                         self.edit_tag(dialog.get_tag(), row)

#             else:
#                 self.add_tag(dialog.get_tag())

#     def _on_edit_tag(self):
#         dialog = TagDialog(self)

#         item = self.view.currentItem()
#         dialog.set_tag(self._item_to_tag(item))

#         if dialog.exec() == QDialog.Accepted:

#             tag = dialog.get_tag()
#             self.edit_tag(tag, self.view.currentRow())

#     def _on_rem_tag(self):
#         """Remove selected tags"""

#         items = []
#         for index in self.view.selectionModel().selectedRows():
#             items.append(self.view.takeItem(index.row()))

#         for item in items:
#             del item

if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)

    w = ClassificationEditor()

    w.set_classifications(
        [
            {"name": "Pathogene", "color": "red", "number": 324, "description": "test"},
            {
                "name": "Likly Pathogene",
                "color": "orange",
                "number": 324,
                "description": "test",
            },
            {"name": "Benin", "color": "purple", "number": 324, "description": "test"},
            {"name": "boby", "color": "orange", "number": 324, "description": "test"},
        ]
    )

    w.show()

    app.exec()
