from PySide2.QtCore import *
from PySide2.QtWidgets import *
from PySide2.QtGui import *

from .plugin import VariantPluginWidget
from cutevariant.gui.ficon import FIcon


class InfoVariantWidget(VariantPluginWidget):

    #  TODO: make these settings common with ColumnQueryModel
    # map value type to color
    colors = {
        "str": "#27A4DD",  # blue
        "bool": "#F1646C",  # red
        "float": "#9DD5C0",  # light blue
        "int": "#FAC174",  # light yellow
        "NoneType": "#FFFFFF",  # white
    }

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
            #  TODO: Decide if None types must be displayed
            item.setIcon(
                0, FIcon(0xF70A, InfoVariantWidget.colors[val.__class__.__name__])
            )

            self.view.addTopLevelItem(item)
