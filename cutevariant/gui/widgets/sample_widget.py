import sqlite3
from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

from cutevariant.gui.widgets import MarkdownEditor
from cutevariant.core import sql
from cutevariant.config import Config

from cutevariant.gui.ficon import FIcon

from cutevariant.gui.model_view.edit_box_table import EditBoxTableModel, EditBoxTableView, get_variants_classif_stats, get_variants_valid_stats, get_validated_variants_table
from cutevariant.gui.widgets import ChoiceButton, DictWidget, TagEdit


class QVline(QFrame):
    def __init__(self):
        super().__init__()
        self.setFrameShape(QFrame.VLine)
        self.setFrameShadow(QFrame.Sunken)

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
        self.conn = conn
        self.TAG_SEPARATOR = "&"

        # self.REVERSE_CLASSIF = {v["name"]: k for k, v in self.SAMPLE_CLASSIFICATION.items()}

        # Identity
        self.name_edit = QLineEdit()
        self.name_edit.setReadOnly(True)
        self.fam_edit = QLineEdit()
        self.tab_widget = QTabWidget()
        self.classification = QComboBox()
        self.tag_edit = TagEdit()
        self.tag_button = QToolButton()
        self.tag_button.setAutoRaise(True)
        self.tag_button.setIcon(FIcon(0xF0349))

        self.tag_layout = QHBoxLayout()
        self.tag_layout.setContentsMargins(0, 0, 0, 0)
        self.tag_layout.addWidget(self.tag_edit)

        identity_widget = QWidget()
        identity_layout = QFormLayout(identity_widget)

        identity_layout.addRow("Name", self.name_edit)
        identity_layout.addRow("Family", self.fam_edit)

        identity_layout.addRow("Tags", self.tag_layout)
        identity_layout.addRow("Statut", self.classification)

        self.tag_choice = ChoiceButton()
        # self.tag_choice_action = QWidgetAction(self)
        # self.tag_choice_action.setDefaultWidget(self.tag_choice)

        self.menu = QMenu()
        # self.menu.addAction(self.tag_choice_action)

        self.tag_button.setMenu(self.menu)
        self.tag_button.setPopupMode(QToolButton.InstantPopup)

        # validation
        val_layout = QFormLayout()

        # val_layout.addWidget(self.lock_button)
        # val_layout.addWidget(QComboBox())

        # phenotype
        self.sex_combo = QComboBox()
        self.sex_combo.addItems(["Unknown", "Male", "Female"])
        self.phenotype_combo = QComboBox()  # case /control
        self.phenotype_combo.addItems(["Missing", "Unaffected", "Affected"])

        # comment
        # self.tag_edit = QLineEdit()
        # self.tag_edit.setPlaceholderText("Tags separated by comma ")
        self.comment = MarkdownEditor()
        self.comment.preview_btn.setText("Preview/Edit comment")

        identity_layout.addRow("Comment", self.comment)

        self.hpo_widget = HpoWidget()

        pheno_widget = QWidget()
        pheno_layout = QFormLayout(pheno_widget)
        pheno_layout.addRow("Sexe", self.sex_combo)
        pheno_layout.addRow("Affected", self.phenotype_combo)
        # pheno_layout.addRow("HPO", self.hpo_widget) #hidden for now
        self.tab_widget.addTab(identity_widget, "Edit")
        self.tab_widget.addTab(pheno_widget, "Phenotype")

        stats_widget = QWidget()
        self.variants_stats_view = EditBoxTableView()
        self.valid_stats_view = EditBoxTableView()
        stats_layout = QHBoxLayout()
        stats_layout.addWidget(self.variants_stats_view)
        stats_layout.addWidget(QVline())
        stats_layout.addWidget(self.valid_stats_view)
        stats_widget.setLayout(stats_layout)
        self.tab_widget.addTab(stats_widget, "Variants stats")

        self.validated_view = EditBoxTableView()
        self.tab_widget.addTab(self.validated_view, "Validated variants")

        self.history_view = DictWidget()
        self.history_view.view.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeToContents
        )
        self.history_view.set_headers(["Date", "Modifications"])
        self.tab_widget.addTab(self.history_view, "History")

        header_layout = QHBoxLayout()
        header_layout.addLayout(val_layout)

        vLayout = QVBoxLayout()
        vLayout.addLayout(header_layout)
        vLayout.addWidget(self.tab_widget)

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        vLayout.addLayout(button_layout)

        self.setLayout(vLayout)

    # def on_tab_change(self):
    #     self.adjustSize()

    def load(self, sample_id: int):

        self.sample_id = sample_id
        data = sql.get_sample(self.conn, sample_id)
        self.initial_db_validation = self.get_validation_from_data(data)
        print("loaded data:", data)
        self.name_edit.setText(data.get("name", "?"))
        self.fam_edit.setText(data.get("family_id", "?"))
        self.sex_combo.setCurrentIndex(data.get("sex", 0))
        self.phenotype_combo.setCurrentIndex(data.get("phenotype", 0))

        config = Config("classifications")
        self.CLASSIFICATIONS = config.get("samples", [])

        for item in self.CLASSIFICATIONS:
            self.classification.addItem(FIcon(0xF012F, item["color"]), item["name"], item["number"])

        index = self.classification.findData(data["classification"])
        self.classification.setCurrentIndex(index)

        # self.tag_edit.setText(self.TAG_LIST.index(tag)).setData(Qt.Checked, Qt.CheckStateRole)

        self.comment.setPlainText(data.get("comment", ""))
        self.comment.preview_btn.setChecked(True)
        self.history_view.set_dict(self.get_history_samples())

        self.setWindowTitle("Sample edition: " + data.get("name", "Unknown"))
        self.initial_state = self.get_gui_state()

        variants_stats, header = get_variants_classif_stats(self.conn, self.sample_id)
        self.variants_stats_model = EditBoxTableModel(variants_stats, header)
        self.variants_stats_view.setModel(self.variants_stats_model)

        valid_stats, header = get_variants_valid_stats(self.conn, self.sample_id)
        self.valid_stats_model = EditBoxTableModel(valid_stats, header)
        self.valid_stats_view.setModel(self.valid_stats_model)

        for view in (self.variants_stats_view, self.valid_stats_view):
            h_header = view.horizontalHeader()
            h_header.setStretchLastSection(True)

        validated_variants, header = get_validated_variants_table(self.conn, self.sample_id)
        self.variant_model = EditBoxTableModel(validated_variants, header)
        self.validated_view.setModel(self.variant_model)


    def save(self, sample_id: int):
        """
        Two checks to perform:
         - did the user change any value through the interface?
         - is the database state the same as when the dialog was first opened?
        If yes and yes, update sample_has_variant
        """
        current_state = self.get_gui_state()
        if current_state == self.initial_state:
            return

        current_db_data = sql.get_sample(self.conn, self.sample_id)
        current_db_validation = self.get_validation_from_data(current_db_data)
        if current_db_validation != self.initial_db_validation:
            ret = QMessageBox.warning(
                None,
                "Database has been modified by another user.",
                "Do you want to overwrite value?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if ret == QMessageBox.No:
                return

        # avoid losing tags who exist in DB but not in config.yml

        data = {
            "id": sample_id,
            "name": self.name_edit.text(),
            "family_id": self.fam_edit.text(),
            "sex": self.sex_combo.currentIndex(),
            "phenotype": self.phenotype_combo.currentIndex(),
            "classification": self.classification.currentData(),
            "tags": self.TAG_SEPARATOR.join(self.tag_edit.text().split(",")),
            "comment": self.comment.toPlainText(),
        }

        sql.update_sample(self.conn, data)

    def get_validation_from_data(self, data):
        return {
            "fam": data["family_id"],
            "tags": data["tags"],
            "comment": data["comment"],
            "classification": int("{classification}".format(**data)),
            "sex": data["sex"],
            "phenotype": data["phenotype"],
        }

    def get_gui_state(self):
        """
        Used to identify if any writable value was changed by an user when closing the widget
        """
        values = []
        values.append(self.fam_edit.text())
        values.append(self.classification.currentIndex())
        values.append(self.tag_edit.text())
        values.append(self.comment.toPlainText())
        values.append(self.sex_combo.currentIndex())
        values.append(self.phenotype_combo.currentIndex())
        return values

    def get_history_samples(self):
        """Get the history of samples"""
        results = {}
        for record in sql.get_histories(self.conn, "samples", self.sample_id):

            message = "{user} changed {field} from {before} to {after}".format(**record)
            results[record["timestamp"]] = message

        return results


class SampleDialog(QDialog):
    def __init__(self, conn, sample_id, parent=None):
        super().__init__()

        self.sample_id = sample_id
        self.w = SampleWidget(conn)
        self.button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        vLayout = QVBoxLayout(self)
        vLayout.addWidget(self.w)
        vLayout.addWidget(self.button_box)

        self.load()

        self.button_box.accepted.connect(self.save)
        self.button_box.rejected.connect(self.reject)

        # self.resize(800, 600)

    def load(self):
        self.w.load(self.sample_id)
        self.setWindowTitle(self.w.windowTitle())

    def save(self):
        self.w.save(self.sample_id)
        self.accept()


if __name__ == "__main__":
    import sys
    from cutevariant.core import sql

    app = QApplication(sys.argv)

    # conn = sql.get_sql_connection("/home/sacha/exome/exome.db")
    conn = sql.get_sql_connection("C:/Users/Ichtyornis/Projects/cutevariant/may2022.db")

    w = SampleDialog(conn, 1)

    w.show()

    app.exec_()
