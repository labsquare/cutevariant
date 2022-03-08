import html
import sqlite3
from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

from cutevariant.core import sql
from cutevariant.commons import SAMPLE_VARIANT_CLASSIFICATION
from cutevariant.gui.widgets import ChoiceWidget, DictWidget, MarkdownEditor

from cutevariant.gui.ficon import FIcon

from cutevariant.gui.widgets.multi_combobox import MultiComboBox


class SampleVariantWidget(QWidget):
    def __init__(self, conn: sqlite3.Connection, parent=None):
        super().__init__()
        self._conn = conn

        #Title
        self.title = QLabel()
        self.title.setTextFormat(Qt.RichText)

        # Validation
        self.classification = QComboBox()
        self.tab_widget = QTabWidget()
        self.valid_check = QCheckBox("Dossier validé ")
        self.tag_edit = MultiComboBox()
        self.tag_button = QToolButton()
        self.tag_button.setAutoRaise(True)
        self.tag_button.setIcon(FIcon(0xF0349))

        self.tag_layout = QHBoxLayout()
        self.tag_layout.setContentsMargins(0, 0, 0, 0)
        self.tag_layout.addWidget(self.tag_edit)

        validation_box = QGroupBox()
        validation_layout = QFormLayout(validation_box)

        validation_layout.addRow("Classification", self.classification)
        validation_layout.addRow("Tags", self.tag_layout)
        validation_layout.addRow("Statut", self.valid_check)

        self.tag_choice = ChoiceWidget()
        self.tag_choice.add_item(QIcon(), "boby")
        self.tag_choice.add_item(QIcon(), "boby")
        self.tag_choice_action = QWidgetAction(self)
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

        # sample and variant information
        self.var_info = DictWidget()
        self.sample_info = DictWidget()

        info_widget = QWidget()
        info_layout = QHBoxLayout()
        
        var_layout = QVBoxLayout()
        self.var_title = QLabel("Variant")
        self.var_title.setAlignment(Qt.AlignCenter)
        var_layout.addWidget(self.var_title)
        var_layout.addWidget(self.var_info)
        
        sample_layout = QVBoxLayout()
        self.sample_title = QLabel("Sample")
        self.sample_title.setAlignment(Qt.AlignCenter)
        sample_layout.addWidget(self.sample_title)
        sample_layout.addWidget(self.sample_info)
        
        info_layout.addLayout(var_layout)
        info_layout.addLayout(sample_layout)
        info_widget.setLayout(info_layout)
        self.tab_widget.addTab(info_widget, "Information")

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
        header_layout.addWidget(validation_box)
        header_layout.addLayout(val_layout)

        vLayout = QVBoxLayout()
        vLayout.addWidget(self.title)
        vLayout.addLayout(header_layout)
        vLayout.addWidget(self.tab_widget)

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        vLayout.addLayout(button_layout)

        self.setLayout(vLayout)

    def load(self, var: dict, sample: dict, sample_has_var: dict):

        var_name = "{chr}-{pos}-{ref}-{alt}".format(**var)
        
        self.title.setText('<html><head/><body><p align="center"><span style=" font-weight:700;">Validation status of variant </span><span style=" font-weight:700; color:#ff0000;">' 
                            + html.escape(var_name)
                            + '</span><span style=" font-weight:700;"> in sample </span><span style=" font-weight:700; color:#ff0000;">'
                            + str(sample["name"])
                            + '</span></p></body></html>'
                        )
                        

        classif_values = [v for v in SAMPLE_VARIANT_CLASSIFICATION.values()]
        self.classification.addItems(classif_values)
        self.classification.setCurrentIndex(sample_has_var["classification"])
        
        self.var_title.setText(var_name)
        self.sample_title.setText(sample["name"])
        self.var_info.set_dict({k: v for k, v in sample_has_var.items() if k not in ("variant_id", "sample_id", "classification")})
        self.sample_info.set_dict({k: v for k, v in sample.items() if k not in ("name", "id", "comment")})
        # self.sex_combo.setCurrentIndex(data.get("sex", 0))
        # self.phenotype_combo.setCurrentIndex(data.get("phenotype", 0))

        # self.comment_edit.setPlainText(data.get("comment", ""))

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


class SampleVariantDialog(QDialog):
    def __init__(self, conn, sample_id, current_variant, parent=None):
        super().__init__()

        self.sample_id = sample_id
        self.var_data = current_variant
        self.sample_data = sql.get_sample(conn, sample_id)
        self.sample_has_var_data = sql.get_sample_annotations(conn, current_variant["id"], sample_id)

        self.w = SampleVariantWidget(conn)
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
        self.w.load(self.var_data, self.sample_data, self.sample_has_var_data)

    def save(self):
        self.w.save(self.sample_id)
        self.accept()


if __name__ == "__main__":
    import sys
    from cutevariant.core import sql

    app = QApplication(sys.argv)

    conn = sql.get_sql_connection("/home/sacha/test.db")

    w = SampleVariantDialog(conn, 1)

    w.show()

    app.exec_()
