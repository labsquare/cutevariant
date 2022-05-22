import sys

import time

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

from csv_dialog import CSVDialog
from vcf_dialog import VCFDialog
from cutevariant.core.writer.abstractwriter import AbstractWriter

import sqlite3
from cutevariant.core import sql
import cutevariant.constants as cst

import cutevariant.commons as cm


class ExportDialog(QWidget):
    """
    Export dialog base class. Responsible for:
    - Get save file name
    - Call the right dialog, depending on the extension the user wants to export to
    - Display a progress dialog on save
    """

    EXPORT_FORMATS = {"csv": CSVDialog, "vcf": VCFDialog}

    def __init__(self, parent=None):
        super().__init__(parent)

        self.conn = None

        self.setWindowTitle(self.tr("Export database"))

        self.description_label = QLabel(self.tr("Welcome to the export database plugin."))
        self.spacer = QSpacerItem(0, 80)

        self.combo_format = QComboBox(self)
        self.combo_format.clear()
        self.combo_format.addItems(ExportDialog.EXPORT_FORMATS.keys())

        self.button_export = QPushButton(self.tr("Export..."), self)
        self.save_file_name = ""
        self.button_export.pressed.connect(self.get_save_file_name)

        # Position the widgets on the grid, manually, not using Qt designer
        self.grid_layout = QGridLayout(self)
        self.grid_layout.addWidget(self.description_label, 0, 0, 1, 2)
        self.grid_layout.addItem(self.spacer, 1, 0, 1, 2)
        self.grid_layout.addWidget(self.combo_format, 2, 0, 1, 1)
        self.grid_layout.addWidget(self.button_export, 2, 1, 1, 1)

        # For future reference, store the appropriate export dialog as a member of this widget
        self.specialized_export_dialog: AbstractWriterDialog = None

    def get_save_file_name(self) -> None:
        if self.conn is None:
            LOGGER.warning("No database connected, aborting")
            return

        settings = QSettings()
        export_path = QDir.homePath()

        # Not working, I didn't understand how to use QSettings (but this is not crucial for now)
        if settings.contains("save_paths/export_path"):
            export_path = settings.value("save_paths/export_path", export_path)

        extension_name = self.combo_format.currentText()
        f_name = QFileDialog.getSaveFileName(
            self,
            self.tr("Please select a file name you would like to export to"),
            export_path,
            self.tr(f"{extension_name.upper()} file (*.{extension_name})"),
        )[0]
        # PySide differs from C++ Qt in that it returns a tuple that starts with the path instead of just the path...

        if f_name:
            self.save_file_name = f_name
            self.combo_format.hide()  # We don't need it anymore

            # Make sure the extension of the save file name matches the extension_name (even though you can write csv data to a file called export.vcf)
            if not self.save_file_name.endswith(f".{extension_name}"):
                self.save_file_name += f".{extension_name}"  # At 11PM, cannot do better...

            # Open the export dialog according to the chosen extension.
            # The specialized dialog needs sql connection, a file name to save the exported file to, and self (parent widget)
            self.specialized_export_dialog = ExportDialog.EXPORT_FORMATS[extension_name](
                self.conn, self.save_file_name, self
            )
            LOGGER.debug("Instantiated CSV dialog with filename %s", self.save_file_name)

            self.specialized_export_dialog.accepted.connect(self.save)
            self.specialized_export_dialog.rejected.connect(self.cancel_export)

            self.specialized_export_dialog.show()  # Don't forget to show it ;)

    def cancel_export(self):
        """
        Makes sure that at any point, if the user wants to abort any step, this widget gets reset
        """
        LOGGER.debug("Resetting export dialog")
        self.combo_format.show()
        self.save_file_name = ""

    def save(self):
        """
        At this point, the user has selected the file type, name, and fields to export
        So using the specialized dialog, we save the file using the appropriate writer
        """
        if self.conn is None:
            LOGGER.debug("No database to save from, aborting")
            return

        if self.specialized_export_dialog is None:
            LOGGER.debug("No export dialog was created, please report a bug (this is serious)")

        writer: AbstractWriter = self.specialized_export_dialog.writer()

        progress = QProgressDialog(
            self.tr("Saving database to VCF file, please wait..."),
            self.tr("Abort"),
            0,
            writer.total_count(),
            self,
        )
        progress.setWindowModality(Qt.WindowModal)
        progress.show()

        for i, total in writer.async_save():
            progress.setValue(i)

            if progress.wasCanceled():
                break

        self.close()


class TestWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        file_menu = self.menuBar().addMenu(self.tr("File"))
        open_action = file_menu.addAction(self.tr("Open"))
        open_action.triggered.connect(self.open_db)

        self.button_export = QPushButton(self.tr("Export"))
        self.button_export.pressed.connect(self.show_export_dialog)

        self.label_state = QLabel(
            self.tr("No database loaded yet (File -> Open to load variant sql database)")
        )
        layout = QVBoxLayout()
        layout.addWidget(self.label_state)
        layout.addWidget(self.button_export)

        self.setCentralWidget(QWidget())
        self.centralWidget().setLayout(layout)

        self.export_dialog = None
        self.conn = None

    def open_db(self):
        db_name = QFileDialog.getOpenFileName(
            self,
            self.tr("Chose database to see its fields"),
            QDir.homePath(),
            self.tr("SQL database files (*.db)"),
        )[0]
        if db_name:
            self.conn = sql.get_sql_connection(db_name)
            self.label_state.setText(self.tr("SQL database loaded"))

    def show_export_dialog(self):
        if self.conn:
            self.export_dialog = ExportDialog()
            self.export_dialog.conn = self.conn
            self.export_dialog.show()
        else:
            LOGGER.debug("No database to export CSV from, aborting")


if __name__ == "__main__":

    app = QApplication(sys.argv)

    w = TestWindow()
    w.show()

    app.exec_()
