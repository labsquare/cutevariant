from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *

from csv_dialog import CSVDialog
from vcf_dialog import VCFDialog

import sys

import time


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

        self.description_label = QLabel(
            self.tr("Welcome to the export database plugin.")
        )
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

    def get_save_file_name(self) -> None:
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
            self.save_file_name = f_name[0]
            self.combo_format.hide()  # We don't need it anymore

            # Make sure the extension of the save file name matches the extension_name (even though you can write csv data to a file called export.vcf)
            if not self.save_file_name.endswith(f".{extension_name}"):
                self.save_file_name += (
                    f".{extension_name}"  # At 11PM, cannot do better...
                )

    def save(self):
        progress = QProgressDialog("Copying files...", "Abort Copy", 0, 1000, self)
        progress.setWindowModality(Qt.WindowModal)
        progress.show()

        for i in range(1000):
            progress.setValue(i)

            if progress.wasCanceled():
                break

            [i / i for i in range(1, 1000000)]


if __name__ == "__main__":

    app = QApplication(sys.argv)

    w = ExportDialog()
    w.show()

    app.exec_()