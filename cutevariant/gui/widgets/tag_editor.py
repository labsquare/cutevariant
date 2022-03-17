from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
import typing

# Tags {
#     "name":"tags name",
#     "color":"color",
#     "description": "sdfsdf"
# }


class TagDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__()

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Tag Name ...")
        self.color_edit = QPushButton()
        self.descr_edit = QTextEdit()
        self.descr_edit.setPlaceholderText("Description ...")

        self.btn_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)

        edit_layout = QHBoxLayout()
        edit_layout.addWidget(self.color_edit)
        edit_layout.addWidget(self.name_edit)

        form_layout = QVBoxLayout()
        form_layout.addLayout(edit_layout)
        form_layout.addWidget(self.descr_edit)

        v_layout = QVBoxLayout(self)
        v_layout.addLayout(form_layout)
        v_layout.addWidget(self.btn_box)

        self.color_edit.clicked.connect(self._on_select_color)

        self._set_color("#B7B7B8")

        self.btn_box.rejected.connect(self.reject)
        self.btn_box.accepted.connect(self.accept)

    def set_tag(self, tag: dict):
        self.name_edit.setText(tag.get("name", "Unknown"))
        self._set_color(tag.get("color", "gray"))
        self.descr_edit.setText(tag.get("description", ""))

    def get_tag(self) -> dict:

        tag = dict()

        tag["name"] = self.name_edit.text()
        tag["color"] = self.color_edit.text()
        tag["description"] = self.descr_edit.toPlainText()

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


class TagEditor(QWidget):

    COLOR_ROLE = Qt.UserRole
    DESCRIPTION_ROLE = Qt.UserRole + 1

    def __init__(self, parent=None):
        super().__init__()

        self.view = QListWidget()

        self.view.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.view.selectionModel().selectionChanged.connect(self._on_selection_changed)
        self.view.doubleClicked.connect(self._on_edit_tag)

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

        self._items = []

    def set_tags(self, tags: typing.List[dict]):
        """Set tags
        Args:
            items (dict): {"name":"tag", color:"red", description: "a description"}
        """
        for tag in tags:
            item = self._tag_to_item(tag)
            self.view.addItem(item)

    def get_tags(self) -> typing.List[dict]:
        """Return dict"""

        tags = []
        for row in range(self.view.count()):
            tags.append(self._item_to_tag(self.view.item(row)))

        return tags

    def add_tag(self, tag: dict):
        self.view.addItem(self._tag_to_item(tag))

    def edit_tag(self, tag: dict, row: int):

        old_item = self.view.takeItem(row)
        new_item = self._tag_to_item(tag)
        self.view.insertItem(row, new_item)
        del old_item

    def _on_selection_changed(self):
        select_count = len(self.view.selectionModel().selectedRows())

        self.edit_button.setDisabled(select_count > 1)

    def _item_to_tag(self, item: QListWidgetItem) -> dict:

        tag = dict()
        tag["name"] = item.text()

        tag["color"] = item.data(TagEditor.COLOR_ROLE)
        tag["description"] = item.data(TagEditor.DESCRIPTION_ROLE)

        return tag

    def _tag_to_item(self, tag: dict) -> QListWidgetItem:

        item = QListWidgetItem()
        item.setText(tag.get("name", "Unknown"))
        item.setData(TagEditor.COLOR_ROLE, tag.get("color", "gray"))
        item.setData(TagEditor.DESCRIPTION_ROLE, tag.get("description", ""))
        item.setToolTip(item.data(TagEditor.DESCRIPTION_ROLE))

        pix = QPixmap(64, 64)
        pix.fill(QColor(item.data(TagEditor.COLOR_ROLE)))

        item.setIcon(QIcon(pix))

        return item

    def _on_add_tag(self):

        dialog = TagDialog(self)
        if dialog.exec() == QDialog.Accepted:

            # Check if tag not exists
            tag = dialog.get_tag()
            existing_tags_names = [t["name"] for t in self.get_tags()]

            if tag["name"] in existing_tags_names:
                name = tag["name"]
                ret = QMessageBox.warning(
                    self,
                    f"tag already exists",
                    f"Do you want to overwrite tag `{name}` ?",
                    QMessageBox.Yes | QMessageBox.No,
                )

                if ret == QMessageBox.Yes:
                    items = self.view.findItems(name, Qt.MatchExactly)
                    if items:
                        row = self.view.row(items[0])
                        self.edit_tag(dialog.get_tag(), row)

            else:
                self.add_tag(dialog.get_tag())

    def _on_edit_tag(self):
        dialog = TagDialog(self)

        item = self.view.currentItem()
        dialog.set_tag(self._item_to_tag(item))

        if dialog.exec() == QDialog.Accepted:

            tag = dialog.get_tag()
            self.edit_tag(tag, self.view.currentRow())

    def _on_rem_tag(self):
        """Remove selected tags"""

        items = []
        for index in self.view.selectionModel().selectedRows():
            items.append(self.view.takeItem(index.row()))

        for item in items:
            del item


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)

    w = TagEditor()

    w.set_tags(
        [
            {"name": "boby", "color": "red", "description": "test"},
            {"name": "sacha", "color": "red", "description": "test"},
        ]
    )

    w.show()
    print(w.get_tags())

    app.exec()
