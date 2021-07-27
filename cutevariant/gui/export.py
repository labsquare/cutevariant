import sys
import sqlite3
import time
import os

from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *


from cutevariant.gui.widgets import FieldsEditorWidget
from cutevariant.core.writer import (
    AbstractWriter,
    VcfWriter,
    CsvWriter,
    BedWriter,
    PedWriter,
)

import cutevariant.commons as cm


from cutevariant.core import sql


from cutevariant import LOGGER


class ExportDialog(QDialog):
    """
    Base class for every export dialog.
    Derived classes must implement save (will get called when user presses save)
    """

    def __init__(
        self,
        conn: sqlite3.Connection,
        filename: str,
        fields=["chr", "pos", "ref", "alt"],
        source="variants",
        filters={},
        parent=None,
    ):
        super().__init__(parent)

        self.fields = fields
        self.source = source
        self.filters = filters
        self.conn = conn

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.Cancel | QDialogButtonBox.Save
        )
        self.vlayout = QVBoxLayout(self)

        self.vlayout.addWidget(self.button_box)

        self.button_box.accepted.connect(self.save)
        self.button_box.rejected.connect(self.reject)

        self.filename = filename

        self.setWindowTitle(f"Export to {os.path.basename(self.filename)}")

    def set_central_widget(self, widget: QWidget):

        self.vlayout.insertWidget(0, widget)

    def save(self):
        """
        Called when the user presses 'Save' button
        """
        raise NotImplementedError()

    def save_from_writer(self, writer: AbstractWriter, message: str = None) -> bool:
        """
        Should be called only by subclasses to lauch the progress dialog with the specialized writer they just built.
        Returns True on success, False otherwise
        """

        if writer:
            if not message:
                message = "Saving database to file, please wait..."

            progress_dialog = QProgressDialog(
                self.tr(message),
                self.tr("Abort"),
                0,
                writer.total_count(),
                self,
            )

            progress_dialog.setWindowModality(Qt.WindowModal)
            progress_dialog.show()

            for i in writer.async_save():
                progress_dialog.setValue(i)

                if progress_dialog.wasCanceled():
                    return False

            progress_dialog.close()
            return True

        else:
            return False


class BedExportDialog(ExportDialog):
    """Dialog to export database to a bed file"""

    def __init__(self, conn, filename, fields, source, filters, parent=None):
        super().__init__(conn, filename, fields, source, filters, parent)
        self.set_central_widget(
            QLabel(
                self.tr(
                    "Will export BED file (tab-separated file with CHR, START, END)"
                )
            )
        )

    def save(self):
        with open(self.filename, "w+") as device:
            writer = BedWriter(
                self.conn, device, self.fields, self.source, self.filters
            )

            success = self.save_from_writer(writer, "Saving BED file")
            if success:
                self.accept()
            else:
                self.reject()


class CsvExportDialog(ExportDialog):
    """Dialog to export project to CSV."""

    def __init__(
        self,
        conn: sqlite3.Connection,
        filename: str,
        fields,
        source,
        filters,
        parent=None,
    ):
        super().__init__(conn, filename, fields, source, filters, parent)

        form_layout = QFormLayout()
        self.combo = QComboBox()
        self.combo.addItem(";", ";")
        self.combo.addItem("TAB", "\t")
        self.combo.addItem(",", ",")
        newline = "\n"

        form_layout.addRow(self.tr("Separator"), self.combo)

        self.group_box = QGroupBox()
        self.group_box.setTitle(self.tr("The following fields will be exported"))
        self.group_box.setLayout(QVBoxLayout())

        self.info_view = QListView()
        self.info_view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.info_model = QStringListModel(self.fields)
        self.info_view.setModel(self.info_model)

        self.group_box.layout().addWidget(self.info_view)

        widget = QWidget(self)
        layout = QVBoxLayout(widget)
        layout.addLayout(form_layout)
        layout.addWidget(self.group_box)

        self.set_central_widget(widget)

    def save(self):
        if not self.filename:
            LOGGER.debug("No file name set. Aborting")
            QMessageBox.critical(
                self, self.tr("Error"), self.tr("No file name set. Nothing to save")
            )

        with open(self.filename, "w+") as device:

            writer = CsvWriter(
                self.conn, device, self.fields, self.source, self.filters
            )
            writer.separator = self.combo.currentData()
            success = self.save_from_writer(writer, "Saving CSV file")
            if success:
                self.accept()
            else:
                self.reject()


class PedExportDialog(ExportDialog):
    """Dialog to export database to a bed file"""

    def __init__(self, conn, filename, fields, source, filters, parent=None):
        super().__init__(conn, filename, fields, source, filters, parent)

    def save(self):
        with open(self.filename, "w+") as device:
            writer = PedWriter(self.conn, device)

            success = self.save_from_writer(writer, "Saving PED file")
            if success:
                self.accept()
            else:
                self.reject()


class VcfExportDialog(ExportDialog):
    """
    Dialog to retrieve user choices when exporting to VCF
    """

    def __init__(
        self,
        conn: sqlite3.Connection,
        filename: str,
        fields,
        source,
        filters,
        parent=None,
    ):
        super().__init__(conn, filename, fields, source, filters, parent)

        self.group_box = QGroupBox()
        self.group_box.setTitle(self.tr("The following fields will be exported"))
        self.group_box.setLayout(QVBoxLayout())

        self.info_view = QListView()
        self.info_view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.info_model = QStringListModel(self.fields)
        self.info_view.setModel(self.info_model)

        self.group_box.layout().addWidget(self.info_view)

        widget = QWidget(self)
        layout = QVBoxLayout(widget)
        layout.addWidget(self.group_box)

        self.set_central_widget(self.group_box)

    def save(self):
        with open(self.filename, "w+") as device:
            writer = VcfWriter(
                self.conn, device, self.fields, self.source, self.filters
            )
            success = self.save_from_writer(writer, "Exporting to VCF")

            if success:
                self.accept()
            else:
                self.reject()

        self.close()  # Whatever happens, this dialog is now useless


class ExportDialogFactory:

    FORMATS = {
        "bed": BedExportDialog,
        "csv": CsvExportDialog,
        "vcf": VcfExportDialog,
        "ped": PedExportDialog,
    }

    @classmethod
    def create_dialog(
        cls,
        conn: sqlite3.Connection,
        format_name: str,
        filename: str,
        fields=["chr", "pos", "ref", "alt"],
        source="variants",
        filters={},
    ):
        DialogClass = cls.FORMATS.get(format_name)
        dialog = DialogClass(
            conn,
            filename,
            fields,
            source,
            filters,
        )

        return dialog

    @classmethod
    def get_supported_formats(cls):
        """
        Returns a list of supported export formats
        """
        return cls.FORMATS.keys()


class TestWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        file_menu = self.menuBar().addMenu(self.tr("File"))
        open_action = file_menu.addAction(self.tr("Open"))
        open_action.triggered.connect(self.open_db)

        self.button_export = QPushButton(self.tr("Export"))
        self.button_export.pressed.connect(self.show_export_dialog)

        self.combo_chose_format = QComboBox(self)
        self.combo_chose_format.clear()
        self.combo_chose_format.addItems(ExportDialogFactory.get_supported_formats())

        self.label_state = QLabel(
            self.tr(
                "No database loaded yet (File -> Open to load variant sql database)"
            )
        )
        self.label_fields = QLabel(
            self.tr("Please enter the fields to export (one per line)")
        )
        self.text_edit_fields = QTextEdit("", self)
        self.label_source = QLabel(
            self.tr("Please chose the source you want to export from")
        )

        self.combo_chose_source = QComboBox(self)

        layout = QVBoxLayout()
        layout.addWidget(self.label_state)
        layout.addWidget(self.label_fields)
        layout.addWidget(self.text_edit_fields)
        layout.addWidget(self.combo_chose_source)

        layout.addWidget(self.combo_chose_format)
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

            self.combo_chose_source.clear()
            records = list(sql.get_selections(self.conn))
            sources = [record["name"] for record in records]
            self.combo_chose_source.addItems(sources)

            self.label_state.setText(self.tr("SQL database connected"))

    def show_export_dialog(self):
        if self.conn:
            export_file_name = QFileDialog.getSaveFileName(
                self, self.tr("Please chose a file you want to save to")
            )[0]
            if not export_file_name:
                return
            self.export_dialog = ExportDialogFactory.create_dialog(
                self.conn,
                self.combo_chose_format.currentText(),
                export_file_name,
                self.text_edit_fields.toPlainText().split("\n"),
                self.combo_chose_source.currentText(),
            )
            self.export_dialog.show()
        else:
            LOGGER.debug("No database to export CSV from, aborting")


if __name__ == "__main__":

    app = QApplication(sys.argv)

    w = TestWindow()
    w.show()

    app.exec_()
