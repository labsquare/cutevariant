# Standard imports
import sqlite3

# Qt imports
from PySide6.QtWidgets import (
    QVBoxLayout,
    QFormLayout,
    QTableView,
    QComboBox,
    QGroupBox,
    QLabel,
    QSizePolicy,
    QSpacerItem,
    QDialogButtonBox,
)
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex, QThreadPool
from numpy import array

# Custom imports
from cutevariant.gui.ficon import FIcon
from cutevariant.gui.plugin import PluginDialog
from cutevariant.gui.sql_thread import SqlThread
from cutevariant.core import sql


class ValidationCheckDialog(PluginDialog):

    ENABLE = True

    ALREADY_VALIDATED = 0
    PATHOGENIC = 1
    LIKELY_PATHOGENIC = 2

    def __init__(self, conn=None, parent=None):
        super().__init__(parent)
        self.conn = conn

        # Type combo box
        self.type_combo = QComboBox()
        self.type_combo.addItem(
            FIcon(0xF04E6),
            self.tr("Variants already validated in some samples but not all of them"),
            self.ALREADY_VALIDATED,
        )
        self.type_combo.addItem(
            FIcon(0xF04E6),
            self.tr("Variants not validated but classified as Pathogenic (ACMG-5)"),
            self.PATHOGENIC,
        )
        self.type_combo.addItem(
            FIcon(0xF04E6),
            self.tr(
                "Variants not validated but classified as Pathogenic (ACMG-5) or Likely pathogenic (ACMG-4)"
            ),
            self.LIKELY_PATHOGENIC,
        )

        self.form_box = QGroupBox()

        # Connect to check form
        self.type_combo.currentTextChanged.connect(self.check_form)

        flayout = QFormLayout()
        flayout.addRow(self.tr("Request"), self.type_combo)

        self.form_box.setLayout(flayout)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Cancel | QDialogButtonBox.Apply)
        self.button_box.button(QDialogButtonBox.Apply).setDisabled(False)
        self.button_box.button(QDialogButtonBox.Apply).clicked.connect(self.create_filter)
        self.button_box.rejected.connect(self.reject)

        vlayout = QVBoxLayout()

        self.title = QLabel()
        self.title.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.title.setText(
            """<b>Check Variants validation</b> <br/>
            Choose type of request to select variants presumably miss-validated
            """
        )
        vlayout.addWidget(self.title)
        vlayout.addWidget(self.form_box)
        vlayout.addWidget(self.button_box)
        self.setLayout(vlayout)
        self.resize(300, 100)
        # self.populate()

    def populate(self):
        """Fill combobox with samples from databases"""

        self.mother_combo.clear()
        self.father_combo.clear()
        self.child_combo.clear()

        samples = [i["name"] for i in sql.get_samples(self.conn)]

        for sample in samples:
            self.mother_combo.addItem(FIcon(0xF1077), sample)
            self.father_combo.addItem(FIcon(0xF0643), sample)
            self.child_combo.addItem(FIcon(0xF0E7D), sample)

    def check_form(self):
        """Check if formular is okay and enable apply button
        This methods is triggered by all formular input
        """

        valid_form = True
        self.button_box.button(QDialogButtonBox.Apply).setEnabled(valid_form)

    def create_filter(self, conn: sqlite3.Connection):
        """build filter and send to the mainwindow.set_state_data"""

        filter_type = self.type_combo.currentData()

        # Default request
        request = "SELECT variant_id FROM genotypes WHERE genotypes.classification IN (2) AND genotypes.gt >=1 GROUP BY genotypes.classification, genotypes.variant_id INTERSECT SELECT variant_id FROM genotypes WHERE genotypes.classification IN (0) AND genotypes.gt >=1 GROUP BY genotypes.classification, genotypes.variant_id"

        # Type of request
        if filter_type == self.ALREADY_VALIDATED:
            request = "SELECT distinct(variant_id) FROM genotypes WHERE genotypes.classification IN (2) AND genotypes.gt >=1 GROUP BY genotypes.classification, genotypes.variant_id INTERSECT SELECT variant_id FROM genotypes WHERE genotypes.classification IN (0) AND genotypes.gt >=1 GROUP BY genotypes.classification, genotypes.variant_id"
        elif filter_type == self.PATHOGENIC:
            request = "SELECT distinct(variant_id) FROM genotypes WHERE genotypes.classification IN (0) AND genotypes.gt >=1 AND genotypes.variant_id IN (SELECT id FROM variants WHERE variants.classification IN (5))"
        elif filter_type == self.LIKELY_PATHOGENIC:
            request = "SELECT distinct(variant_id) FROM genotypes WHERE genotypes.classification IN (0) AND genotypes.gt >=1 AND genotypes.variant_id IN (SELECT id FROM variants WHERE variants.classification IN (4,5))"

        # create variant list
        variants = [{"id": record[0]} for record in self.conn.execute(request)]

        # create filters
        if len(variants) != 0:
            filters = {"$or": variants}
        else:
            filters = {"$or": [{"id": 0}]}

        # launch request/filters
        self.mainwindow.set_state_data("filters", filters)
        self.mainwindow.refresh_plugins()
        self.close()


if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)
    conn = sql.get_sql_connection("/home/lebechea/devel/validation_check.db")
    dialog = ValidationCheckDialog(conn=conn)
    dialog.show()
    app.exec_()
