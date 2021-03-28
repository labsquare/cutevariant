from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *

import sqlite3

from abstract_writer_dialog import AbstractWriterDialog
from fields_selection_widget import FieldsEditorWidget

from cutevariant.core.writer import CsvWriter

import cutevariant.commons as cm
import cutevariant.core.command as cmd

LOGGER = cm.logger()


class CSVDialog(AbstractWriterDialog):
    def __init__(self, conn: sqlite3.Connection, filename: str, parent=None):
        super().__init__(conn, filename, parent)

        self.widget_fields_editor = FieldsEditorWidget(self)
        self.widget_fields_editor.set_connection(conn)

        layout = QVBoxLayout()
        layout.addWidget(self.widget_fields_editor)

        self.central_widget.setLayout(layout)

        self.selected_fields = ["chr", "pos", "ref", "alt"]

    def writer(self) -> AbstractWriterDialog:

        selected_fields = self.widget_fields_editor.get_selected_fields()
        selected_fields_as_list = []
        for category, fields in selected_fields.items():
            # TODO Would be great, sadly with that we end up with suffixes in the header that are not in the fields
            # selected_fields_as_list += [f"{category}.{field}" for field in fields]

            selected_fields_as_list += [field for field in fields]
        # LOGGER.debug("Selected fields", str(selected_fields_as_list)) Displays warning about not being able to format the message

        device = open(self.filename, "w+")
        csv_writer = CsvWriter(self.conn, device)
        csv_writer.fields = selected_fields_as_list

        return csv_writer
