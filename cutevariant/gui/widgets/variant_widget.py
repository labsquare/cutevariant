from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

from cutevariant.gui.widgets import DictWidget
from cutevariant.core import sql
import sqlite3


class VariantWidget(QWidget):
    def __init__(self, conn: sqlite3.Connection, parent=None):
        super().__init__()

        self._conn = conn
        info_box = QGroupBox()
        info_layout = QFormLayout(info_box)
        self.name_edit = QLineEdit()
        self.classification = QComboBox()

        self.name_edit.setReadOnly(True)

        info_layout.addRow("Name", self.name_edit)
        info_layout.addRow("Classification", self.classification)

        self.variant_view = DictWidget()
        self.ann_view = DictWidget()
        self.sample_view = DictWidget()

        self.tab_widget = QTabWidget()

        self.ann_combo = QComboBox()
        self.ann_combo.currentIndexChanged.connect(self.load_annotation)
        self.ann_widget = QWidget()
        ann_layout = QVBoxLayout(self.ann_widget)
        ann_layout.addWidget(self.ann_combo)
        ann_layout.addWidget(self.ann_view)

        self.tab_widget.addTab(self.variant_view, "variants")
        self.tab_widget.addTab(self.ann_widget, "Annotations")
        self.tab_widget.addTab(self.sample_view, "Samples")

        main_layout = QVBoxLayout(self)
        main_layout.addWidget(info_box)
        main_layout.addWidget(self.tab_widget)

        self.data = None

    def save(self, variant_id: int):
        pass

    def load(self, variant_id: int):

        self.data = sql.get_variant(
            self._conn, variant_id, with_annotations=True, with_samples=True
        )

        name = "{chr}-{pos}-{ref}-{alt}".format(**self.data)

        self.ann_combo.clear()

        if "annotations" in self.data:
            for i in self.data["annotations"]:
                self.ann_combo.addItem(i["transcript"])

        if "samples" in self.data:
            sdata = {i["name"]: i["gt"] for i in self.data["samples"] if i["gt"] > 0}
            self.sample_view.set_dict(sdata)

        self.name_edit.setText(name)

        self.variant_view.set_dict(self.data)

    def load_annotation(self):

        if not self.data:
            return

        current = self.ann_combo.currentIndex()

        if "annotations" in self.data:

            adata = self.data["annotations"][current]
            self.ann_view.set_dict({i: k for i, k in adata.items() if k != ""})


class VariantDialog(QDialog):
    def __init__(self, conn, variant_id, parent=None):
        super().__init__()

        self.variant_id = variant_id
        self.w = VariantWidget(conn)
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel
        )
        vLayout = QVBoxLayout(self)
        vLayout.addWidget(self.w)
        vLayout.addWidget(self.button_box)

        self.load()

        self.button_box.accepted.connect(self.save)
        self.button_box.rejected.connect(self.reject)

        self.resize(800, 600)

    def load(self):
        self.w.load(self.variant_id)

    def save(self):
        self.w.save(self.variant_id)
        self.accept()


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    conn = sql.get_sql_connection("/home/sacha/exome/exome_1.db")

    w = VariantDialog(conn)

    w.load(1)

    w.show()

    app.exec()
