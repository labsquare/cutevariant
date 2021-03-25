from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *


class VCFDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_fields = ["chr", "pos", "ref", "alt"]
