from PySide2.QtCore import *
from PySide2.QtWidgets import *
from PySide2.QtGui import *
from .plugin import VariantPluginWidget


class InfoVariantWidget(VariantPluginWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle(self.tr("Info variants"))
        self.setObjectName("info_variants")  # For window saveState

        self.view = QTreeWidget()
        self.view.setColumnCount(2)
        v_layout = QVBoxLayout()
        v_layout.setContentsMargins(0, 0, 0, 0)
        v_layout.addWidget(self.view)
        self.setLayout(v_layout)

    def set_variant(self, variant):
        self.view.clear()

        # print(variant)
        for key, val in variant.items():
            item = QTreeWidgetItem()
            item.setText(0, str(key))
            item.setText(1, str(val))
            # item.setFlags(Qt.ItemIsSelectable|Qt.ItemIsEnabled)

            self.view.addTopLevelItem(item)
