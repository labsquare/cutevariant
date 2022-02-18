import sqlite3
from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

from cutevariant.gui.widgets import MarkdownEditor
from cutevariant.core import sql

from cutevariant.gui.ficon import FIcon

from cutevariant.gui.widgets import ChoiceWidget
from cutevariant.gui.widgets.multi_combobox import MultiComboBox


class HpoWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__()

        self.view = QListView()
        self.add_button = QToolButton()
        self.add_button.setAutoRaise(True)
        self.add_button.setText("+")
        self.rem_button = QToolButton()
        self.rem_button.setAutoRaise(True)
        self.rem_button.setText("-")

        self.view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.add_button)
        btn_layout.addWidget(self.rem_button)
        btn_layout.setSizeConstraint(QLayout.SetMinimumSize)
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        btn_layout.addWidget(spacer)

        vLayout = QVBoxLayout(self)
        vLayout.addWidget(self.view, 5)
        vLayout.addLayout(btn_layout)
        vLayout.setContentsMargins(0, 0, 0, 0)


class SampleWidget(QWidget):
    def __init__(self, conn: sqlite3.Connection, parent=None):
        super().__init__()
        self._conn = conn

        # Identity
        self.name_edit = QLineEdit()
        self.fam_edit = QLineEdit()
        self.tab_widget = QTabWidget()
        self.valid_check = QCheckBox("Dossier validé ")
        self.tag_edit = MultiComboBox()
        self.tag_button = QToolButton()
        self.tag_button.setAutoRaise(True)
        self.tag_button.setIcon(FIcon(0xF0349))

        self.tag_layout = QHBoxLayout()
        self.tag_layout.setContentsMargins(0, 0, 0, 0)
        self.tag_layout.addWidget(self.tag_edit)

        identity_box = QGroupBox()
        identity_layout = QFormLayout(identity_box)

        identity_layout.addRow("Name ID", self.name_edit)
        identity_layout.addRow("Family ID", self.fam_edit)

        identity_layout.addRow("Tags", self.tag_layout)
        identity_layout.addRow("Statut", self.valid_check)

        self.tag_choice = ChoiceWidget()
        self.tag_choice.add_item(QIcon(), "boby")
        self.tag_choice.add_item(QIcon(), "boby")
        self.tag_choice_action = QWidgetAction(self.tag_choice)
        self.tag_choice_action.setDefaultWidget(self.tag_choice)

        self.menu = QMenu()
        self.menu.addAction(self.tag_choice_action)

        self.tag_button.setMenu(self.menu)
        self.tag_button.setPopupMode(QToolButton.InstantPopup)

        self.tag_edit.addItems(["#hemato", "#cardio", "#pharmaco"])

        # validation
        val_layout = QFormLayout()

        # val_layout.addWidget(self.lock_button)
        # val_layout.addWidget(QComboBox())

        # phenotype
        self.sex_combo = QComboBox()
        self.sex_combo.addItems(["Unknown", "Male", "Female"])
        self.phenotype_combo = QComboBox()  # case /control
        self.phenotype_combo.addItems(["Missing", "Unaffected", "Affected"])

        self.hpo_widget = HpoWidget()

        pheno_widget = QWidget()
        pheno_layout = QFormLayout(pheno_widget)
        pheno_layout.addRow("Sexe", self.sex_combo)
        pheno_layout.addRow("Affected", self.phenotype_combo)
        pheno_layout.addRow("HPO terms", self.hpo_widget)

        self.tab_widget.addTab(pheno_widget, "Phenotype")

        # comment
        self.tag_edit = QLineEdit()
        self.tag_edit.setPlaceholderText("Tags separated by comma ")
        self.comment_edit = MarkdownEditor()
        comm_widget = QWidget()
        comm_layout = QVBoxLayout(comm_widget)
        comm_layout.addWidget(self.tag_edit)
        comm_layout.addWidget(self.comment_edit)

        self.tab_widget.addTab(comm_widget, "Comments")

        header_layout = QHBoxLayout()
        header_layout.addWidget(identity_box)
        header_layout.addLayout(val_layout)

        vLayout = QVBoxLayout()
        vLayout.addLayout(header_layout)
        vLayout.addWidget(self.tab_widget)

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        vLayout.addLayout(button_layout)

        self.setLayout(vLayout)

    def load(self, sample_id: int):

        data = sql.get_sample(self._conn, sample_id)

        self.name_edit.setText(data.get("name", "?"))
        self.fam_edit.setText(data.get("family_id", "?"))
        self.sex_combo.setCurrentIndex(data.get("sex", 0))
        self.phenotype_combo.setCurrentIndex(data.get("phenotype", 0))

        self.comment_edit.setPlainText(data.get("comment", ""))

        print(data)

    def save(self, sample_id: int):

        data = {
            "id": sample_id,
            "name": self.name_edit.text(),
            "family_id": self.fam_edit.text(),
            "sex": self.sex_combo.currentIndex(),
            "phenotype": self.phenotype_combo.currentIndex(),
            "comment": self.comment_edit.toPlainText(),
        }

        sql.update_sample(self._conn, data)


class SampleDialog(QDialog):
    def __init__(self, conn, sample_id, parent=None):
        super().__init__()

        self.sample_id = sample_id
        self.w = SampleWidget(conn)
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel
        )
        vLayout = QVBoxLayout(self)
        vLayout.addWidget(self.w)
        vLayout.addWidget(self.button_box)

        self.load()

        self.button_box.accepted.connect(self.save)
        self.button_box.rejected.connect(self.reject)

        self.resize(800, 600)

    def load(self):
        self.w.load(self.sample_id)

    def save(self):
        self.w.save(self.sample_id)
        self.accept()


if __name__ == "__main__":
    import sys
    from cutevariant.core import sql

    app = QApplication(sys.argv)

    conn = sql.get_sql_connection("/home/sacha/test.db")

    w = SampleDialog(conn, 1)

    w.show()

    app.exec_()
