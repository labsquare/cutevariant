from cutevariant.gui import plugin
from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *


class PierreWidget(plugin.PluginWidget):
    LOCATION = plugin.FOOTER_LOCATION

    def __init__(self):
        super().__init__()
        self.edit = QLineEdit()
        self.edit.setText("rien")

        v_layout = QVBoxLayout()
        v_layout.addWidget(self.edit)

        self.setLayout(v_layout)
