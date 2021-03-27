from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *

import sqlite3

from cutevariant.core.writer import VcfWriter
from .fields_selection_widget import FieldsEditorWidget


class VCFDialog(QDialog):
    """
    This dialog is responsible for asking the VCF fields the user wishes to export.
    It makes sure that all the mandatory fields are selected by the user (by disabling the relevant items)
    The dialog **must** be created using a valid sqlite3 connection
    """

    def __init__(self, conn: sqlite3.Connection, parent=None):
        super().__init__(parent)
        self.selected_fields = ["chr", "pos", "ref", "alt"]

        self.widget_select_fields = FieldsEditorWidget()
        self.widget_select_fields.on_open_project(conn)
        layout = QGridLayout(self)
