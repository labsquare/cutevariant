import sqlite3

from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtWidgets import *

from cutevariant.gui.plugin import PluginDialog
from cutevariant.gui import MainWindow

from cutevariant.core import sql


TAGS_CATEGORIES = ["variants", "samples"]


class TagEditor(QDialog):
    def __init__(self, parent=None):
        super().__init__()

        self.name_edit = QLineEdit()
        self.category = QComboBox()
        self.color_btn = QPushButton()
        self.description = QTextEdit()

        self.btn_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        self.btn_box.accepted.connect(self.accept)
        self.btn_box.rejected.connect(self.reject)

        form_layout = QFormLayout()
        form_layout.addRow("Name", self.name_edit)
        form_layout.addRow("Category", self.category)
        form_layout.addRow("Color", self.color_btn)
        form_layout.addRow("Description", self.description)

        v_layout = QVBoxLayout(self)
        v_layout.addLayout(form_layout)
        v_layout.addWidget(self.btn_box)

        self.category.addItems(TAGS_CATEGORIES)

        self.name_edit.setPlaceholderText("Tags name ...")
        self.description.setPlaceholderText("Tag description ...")

        self.color_btn.clicked.connect(self._edit_color)

    def _edit_color(self):

        color = QColorDialog.getColor()

        if color.isValid():
            self._set_color(color.name())

    def _set_color(self, hex_color: str):
        self.color_btn.setText(hex_color)
        pixmap = QPixmap(64, 64)
        pixmap.fill(QColor(hex_color))
        self.color_btn.setIcon(pixmap)

    def _get_color(self):
        return self.color_btn.text()

    def set_data(
        self,
        name: str,
        description: str,
        color: str = "red",
        category: str = "variants",
    ):

        self.name_edit.setText(name)
        self.description.setText(description)
        self.category.setCurrentText(category)
        self._set_color(color)

    def get_data(self) -> dict:

        return {
            "name": self.name_edit.text(),
            "description": self.description.toPlainText(),
            "category": self.category.currentText(),
            "color": self._get_color(),
        }

    def set_category(self, category: str):
        self.category.setCurrentText(category)


class TagsDialog(PluginDialog):
    """Model class for all tool menu plugins

    These plugins are based on DialogBox; this means that they can be opened
    from the tools menu.
    """

    ENABLE = True

    def __init__(self, conn: sqlite3.Connection, parent: MainWindow = None):
        """
        Keys:
            parent (QMainWindow): cutevariant Mainwindow
        """
        super().__init__(parent)

        self.conn = conn
        self.views = {}

        self.tab = QTabWidget()
        self._add_view("variants")
        self._add_view("samples")

        self.add_btn = QPushButton(self.tr("Add tag..."))
        self.add_btn.clicked.connect(self.on_add)
        self.edit_btn = QPushButton(self.tr("Edit tag..."))
        self.edit_btn.clicked.connect(self.on_edit)
        self.del_btn = QPushButton(self.tr("Delete tag(s)"))
        self.del_btn.clicked.connect(self.on_delete)

        btn_layout = QVBoxLayout()
        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.edit_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.del_btn)

        vLayout = QVBoxLayout()
        vLayout.addWidget(self.tab)

        main_layout = QHBoxLayout(self)
        main_layout.addLayout(vLayout)
        main_layout.addLayout(btn_layout)

        self.load()

    def _add_view(self, name: str):
        view = QListWidget()
        view.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.views[name] = view
        self.tab.addTab(view, name)

    def load(self):

        for category, view in self.views.items():
            view.clear()
            tags = [
                tag for tag in sql.get_tags(self.conn) if tag["category"] == category
            ]

            for tag in tags:
                pix = QPixmap(32, 32)
                pix.fill(tag["color"])

                item = QListWidgetItem()
                item.setText(tag["name"])
                item.setIcon(QIcon(pix))
                item.setToolTip(tag["description"])
                item.setData(Qt.UserRole, tag)
                view.addItem(item)

    def _current_category(self):
        return list(self.views.keys())[self.tab.currentIndex()]

    def _current_view(self):
        return self.views[self._current_category()]

    def on_add(self):

        dialog = TagEditor()
        dialog.set_category(self._current_category())
        if dialog.exec() == QDialog.Accepted:
            sql.insert_tag(self.conn, **dialog.get_data())
            self.load()

    def on_edit(self):

        item = self._current_view().currentItem()
        if item:
            data = item.data(Qt.UserRole)
            dialog = TagEditor()
            dialog.set_data(
                name=data["name"],
                description=data["description"],
                category=data["category"],
                color=data["color"],
            )

            tag_id = data["id"]

            if dialog.exec() == QDialog.Accepted:
                data = dialog.get_data()
                data["id"] = tag_id
                sql.update_tag(self.conn, data)
                self.load()

    def on_delete(self):

        selection = self._current_view().selectionModel().selectedRows()

        if len(selection) == 0:
            return

        ret = QMessageBox.question(
            self,
            "Remove tags",
            "Do you want to remove selected tags ?",
            QMessageBox.Yes | QMessageBox.No,
        )

        if ret == QMessageBox.Yes:

            for index in selection:
                item = self._current_view().item(index.row())
                tag_id = item.data(Qt.UserRole)["id"]
                sql.remove_tag(self.conn, tag_id)

            self.load()


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    conn = sql.get_sql_connection("/home/sacha/test.db")
    # conn.row_factory = sqlite3.Row
    dialog = TagsDialog(conn)
    # dialog.conn = conn
    dialog.exec()
