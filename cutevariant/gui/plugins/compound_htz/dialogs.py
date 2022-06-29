import sqlite3

from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtWidgets import *

from cutevariant.gui.plugin import PluginDialog
from cutevariant.gui import MainWindow
from cutevariant.gui.plugins import compound_htz

class CompoundHtzDialog(PluginDialog):
    """Model class for all tool menu plugins

    These plugins are based on DialogBox; this means that they can be opened
    from the tools menu.
    """

    ENABLE = True

    def __init__(self, conn: sqlite3.Connection, parent: MainWindow=None):
        """
        Keys:
            parent (QMainWindow): cutevariant Mainwindow
        """
        super().__init__(parent)

        self.conn = conn

        group_box = QGroupBox()
        header = QLabel()
        header.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        header.setText(self._get_header_text())
        header_layout = QHBoxLayout()
        header_layout.addWidget(header)
        group_box.setLayout(header_layout)

        #TODO: put in settings
        compound_htz_tag = "#COMPOUND_HTZ"
        self.checkbox = QCheckBox(f"Add tag {compound_htz_tag} to all selected variants", self)

        self.button = QPushButton("Select compound htz variants")
        self.button.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        self.button.clicked.connect(self._on_click)
        button_box = QVBoxLayout()
        button_box.setAlignment(Qt.AlignCenter)
        button_box.addWidget(self.button)

        self.setWindowTitle("Compound htz filter")
        self.vlayout = QVBoxLayout()
        self.vlayout.addWidget(group_box)
        self.vlayout.addWidget(self.checkbox)
        self.vlayout.addLayout(button_box)
        self.setLayout(self.vlayout)

    def _get_header_text(self):
        #TODO: put in settings
        gene_field = "gnomen"
        exclusion_criteria = []

        text = f"""<b>Compound heterozygosity</b> is defined in settings as variants with:
        <ul>
            <li> sample.gt > 0</li>
            <li> same content in field: {gene_field}</li>
        </ul>
        """
        if len(exclusion_criteria) > 0:
            text += "Exclusion criteria:<ul>"
            for e in exclusion_criteria:
                text += "<li> {e}</li>"
            text += "</ul>"
        return text

    def _get_variant_ids(self):
        #TODO
        variants = []
        return variants

    def _on_click(self):
        variants = self._get_variant_ids()

        if len(variants) != 0:
            filters = {"$and": [{"id": {"$in": variants}}]}

            if self.checkbox.checkState():
                print("checked")

            self.mainwindow.set_state_data("filters", filters)
            self.mainwindow.refresh_plugins()

        else:
            QMessageBox.information(
                self, "No compound htz found", "Variant selection was unchanged"
            )

        self.close()

if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    dialog = CompoundHtzDialog()
    # conn = sqlite3.connect("path_to_test_database.db")
    # conn.row_factory = sqlite3.Row
    # dialog.conn = conn
    dialog.exec_()