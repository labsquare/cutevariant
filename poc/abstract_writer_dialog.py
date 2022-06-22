from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

from cutevariant.core.writer import AbstractWriter

import sys

import time
import sqlite3
import cutevariant.constants as cst
import cutevariant.commons as cm

from cutevariant import LOGGER


class AbstractWriterDialog(QDialog):
    """
    This dialog base class is responsible for asking the VCF fields the user wishes to export.
    Specialized classes must make sure that all the mandatory fields are selected by the user (by disabling the *obviously checked* relevant items)
    The dialog **must** :
    - be created using a valid sqlite3 connection, and a file name
    - implement the :writer: method (see below)
    """

    def __init__(self, conn: sqlite3.Connection, filename: str, parent=None):
        super().__init__(parent)
        self.conn = conn
        self.filename = filename

        # Just the OK-Cancel buttons, make sure to connect them to the accept and reject slots
        self.buttons_dialog = QDialogButtonBox(self)
        self.buttons_dialog.setStandardButtons(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons_dialog.accepted.connect(self.accept)
        self.buttons_dialog.rejected.connect(self.reject)
        self.buttons_dialog.show()

        # Central widget is an empty widgets for derived class to settle in
        self.central_widget = QWidget(self)

        layout = QVBoxLayout()
        layout.addWidget(self.central_widget)
        layout.addWidget(self.buttons_dialog)

        self.setLayout(layout)

    def writer(self) -> AbstractWriter:
        """
        Returns a valid concrete writer constructed with user choices
        """
        raise NotImplementedError()
