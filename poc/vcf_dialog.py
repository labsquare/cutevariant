# from PySide2.QtWidgets import *
# from PySide2.QtCore import *
# from PySide2.QtGui import *

# import sqlite3

# from cutevariant.core.writer import VcfWriter, AbstractWriter
# from fields_selection_widget import FieldsEditorWidget
# from abstract_writer_dialog import AbstractWriterDialog


# class VCFDialog(AbstractWriterDialog):
#     """
#     This dialog is responsible for asking the VCF fields the user wishes to export.
#     It makes sure that all the mandatory fields are selected by the user (by disabling the *obviously checked* relevant items)
#     The dialog **must** be created using a valid sqlite3 connection
#     """

#     def __init__(self, conn: sqlite3.Connection, filename: str, parent=None):
#         super().__init__(conn, filename, parent)
#         self.selected_fields = ["chr", "pos", "ref", "alt"]

#         self.widget_select_fields = FieldsEditorWidget()
#         self.widget_select_fields.set_connection(conn)
#         layout = QGridLayout(self)

#     def writer(self) -> AbstractWriter:
#         pass
