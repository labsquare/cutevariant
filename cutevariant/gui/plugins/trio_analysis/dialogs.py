# Standard imports
import sqlite3

# Qt imports
from PySide2.QtWidgets import (
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
from PySide2.QtCore import Qt, QAbstractTableModel, QModelIndex, QThreadPool

# Custom imports
from cutevariant.gui.ficon import FIcon
from cutevariant.gui.plugin import PluginDialog
from cutevariant.gui.sql_thread import SqlThread
from cutevariant.core import sql


class TrioAnalysisDialog(PluginDialog):

    ENABLE = True

    DE_NOVO = 0
    AUTOSOMAL_RECESSIVE = 1
    AUTOSOMAL_DOMINANT = 2
    X_LINKED_RECESSIVE = 3

    def __init__(self, conn=None, parent=None):
        super().__init__(parent)
        self.conn = conn

        self.type_combo = QComboBox()

        self.type_combo.addItem(self.tr("De novo mutation"), self.DE_NOVO)
        self.type_combo.addItem(
            self.tr("Autosomal Recessive"), self.AUTOSOMAL_RECESSIVE
        )
        self.type_combo.addItem(self.tr("Autosomal Dominant"), self.AUTOSOMAL_DOMINANT)
        self.type_combo.addItem(self.tr("X-linked Recessive"), self.X_LINKED_RECESSIVE)

        self.form_box = QGroupBox()
        self.father_combo = QComboBox()
        self.mother_combo = QComboBox()
        self.child_combo = QComboBox()

        # Connect to check form
        self.type_combo.currentTextChanged.connect(self.check_form)
        self.father_combo.currentTextChanged.connect(self.check_form)
        self.mother_combo.currentTextChanged.connect(self.check_form)
        self.child_combo.currentTextChanged.connect(self.check_form)

        flayout = QFormLayout()
        flayout.addRow(self.tr("Type"), self.type_combo)

        # add spacer

        # flayout.addItem(QSpacerItem(0, 10))
        flayout.addRow(self.tr("Father"), self.father_combo)
        flayout.addRow(self.tr("Mother"), self.mother_combo)
        flayout.addRow(self.tr("Child"), self.child_combo)

        self.form_box.setLayout(flayout)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.Apply | QDialogButtonBox.Cancel
        )
        self.button_box.button(QDialogButtonBox.Apply).setDisabled(True)
        self.button_box.button(QDialogButtonBox.Apply).clicked.connect(
            self.create_filter
        )
        self.button_box.rejected.connect(self.reject)

        vlayout = QVBoxLayout()

        self.title = QLabel()
        self.title.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.title.setText(
            """<b>Create Trio analysis filters</b> <br/>
            Set samples to the corresponding parents
            """
        )
        vlayout.addWidget(self.title)
        vlayout.addWidget(self.form_box)
        vlayout.addWidget(self.button_box)
        self.setLayout(vlayout)
        self.resize(600, 300)
        self.populate()

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

        #  Check if all samples are unique
        valid_form = False
        samples = {
            self.mother_combo.currentText(),
            self.father_combo.currentText(),
            self.child_combo.currentText(),
        }

        if len(samples) == 3:
            valid_form = True

        self.button_box.button(QDialogButtonBox.Apply).setEnabled(valid_form)

    def create_filter(self):
        """ build filter and send to the mainwindow.set_state_data """

        filter_type = self.type_combo.currentData()

        father = self.father_combo.currentText()
        mother = self.mother_combo.currentText()
        child = self.child_combo.currentText()

        if filter_type == self.DE_NOVO:
            filters = {
                "AND": [
                    {"field": ("sample", father, "gt"), "operator": "=", "value": 0},
                    {"field": ("sample", mother, "gt"), "operator": "=", "value": 0},
                    {"field": ("sample", child, "gt"), "operator": "=", "value": 1},
                ]
            }

        elif filter_type == self.AUTOSOMAL_RECESSIVE:
            filters = {
                "AND": [
                    {"field": ("sample", father, "gt"), "operator": "=", "value": 1},
                    {"field": ("sample", mother, "gt"), "operator": "=", "value": 1},
                    {"field": ("sample", child, "gt"), "operator": "=", "value": 2},
                ]
            }

        elif filter_type == self.AUTOSOMAL_DOMINANT:
            filters = {
                "AND": [
                    {"field": ("sample", child, "gt"), "operator": "=", "value": 1.0},
                    {
                        "OR": [
                            {
                                "AND": [
                                    {
                                        "field": ("sample", father, "gt"),
                                        "operator": "=",
                                        "value": 1.0,
                                    },
                                    {
                                        "field": ("sample", mother, "gt"),
                                        "operator": "=",
                                        "value": 0.0,
                                    },
                                ]
                            },
                            {
                                "AND": [
                                    {
                                        "field": ("sample", father, "gt"),
                                        "operator": "=",
                                        "value": 0.0,
                                    },
                                    {
                                        "field": ("sample", mother, "gt"),
                                        "operator": "=",
                                        "value": 1.0,
                                    },
                                ]
                            },
                        ]
                    },
                ]
            }

        elif filter_type == self.X_LINKED_RECESSIVE:
            filters = {
                "AND": [
                    {"field": "chr", "operator": "=", "value": "X"},
                    {"field": ("sample", father, "gt"), "operator": "=", "value": 0},
                    {"field": ("sample", mother, "gt"), "operator": "=", "value": 1},
                    {"field": ("sample", child, "gt"), "operator": ">", "value": 0},
                ]
            }

        self.mainwindow.set_state_data("filters",filters)
        self.mainwindow.refresh_plugins()
        self.close()


if __name__ == "__main__":
    from PySide2.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)
    conn = sql.get_sql_connection("/home/sacha/Dev/corpasome.db")
    dialog = TrioAnalysisDialog(conn=conn)
    dialog.show()
    app.exec_()
