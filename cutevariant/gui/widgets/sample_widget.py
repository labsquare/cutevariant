import sqlite3
from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

from cutevariant.gui.widgets import MarkdownEditor
from cutevariant.core import sql
from cutevariant.config import Config

from cutevariant.gui.ficon import FIcon

from cutevariant.gui.widgets import DictWidget, TagEdit
from cutevariant.gui.widgets.multi_combobox import MultiComboBox

from cutevariant.gui.widgets import ChoiceButton


class AbstractSectionWidget(QWidget):
    def __init__(self, parent: QWidget = None):
        super().__init__()

        self.conn = None

    def set_sample(self, sample: dict):
        raise NotImplementedError

    def get_sample(self) -> dict:
        raise NotImplementedError


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


class EvaluationSectionWidget(AbstractSectionWidget):
    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.TAG_SEPARATOR = "&"
        self.setWindowTitle("Evaluation")
        self.setToolTip("You can edit sample information")
        main_layout = QFormLayout()

        self.family_edit = QLineEdit()

        self.class_combo = QComboBox()
        self.tag_edit = TagEdit()
        self.tag_edit.setPlaceholderText(self.tr("Tag separated by comma ..."))
        self.tag_layout = QHBoxLayout()
        self.tag_layout.setContentsMargins(0, 0, 0, 0)
        self.tag_layout.addWidget(self.tag_edit)

        self.edit_comment_btn = QPushButton("Edit comment")
        self.edit_comment_btn.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Minimum)

        self.comment = MarkdownEditor()
        self.comment.preview_btn.setText("Preview/Edit comment")

        main_layout.addRow("Family", self.family_edit)
        main_layout.addRow("Classification", self.class_combo)
        main_layout.addRow("Tags", self.tag_layout)
        main_layout.addRow("Comment", self.comment)
        self.setLayout(main_layout)

        # Load classification
        config = Config("classifications")
        self.sample_classification = config.get("samples")
        for item in self.sample_classification:
            self.class_combo.addItem(
                FIcon(0xF012F, item.get("color", "gray")),
                item["name"],
                userData=item["number"],
            )

    def get_sample(self) -> dict:
        sample = {
            "family_id": self.family_edit.text(),
            "classification": self.class_combo.currentData(),
            "tags": "&".join([tag for tag in self.tag_edit.text().split(",") if tag]),
            "comment": self.comment.toPlainText(),
        }

        return sample

    def set_sample(self, sample: dict):

        # Load family
        if "family_id" in sample:
            self.family_edit.setText(sample["family_id"])

        # Load tags
        if "tags" in sample:
            self.tag_edit.setText(",".join(sample["tags"].split(self.TAG_SEPARATOR)))

        # Load comment
        if "comment" in sample:
            self.comment.setPlainText(sample["comment"])
            self.comment.preview_btn.setChecked(True)

        # Load classification
        if "classification" in sample:
            self.class_combo.setCurrentText(
                next(
                    (
                        item["name"]
                        for item in self.sample_classification
                        if item["number"] == sample["classification"]
                    ),
                    "Unknown",
                )
            )


class PhenotypeSectionWidget(AbstractSectionWidget):
    def __init__(self, parent: QWidget = None):
        super().__init__(parent)

        self.setWindowTitle("Phenotype")
        self.setToolTip("You can edit phenotype information")
        self.view = QFormLayout()

        #values based on https://gatk.broadinstitute.org/hc/en-us/articles/360035531972-PED-Pedigree-format
        self.sex_combo = QComboBox()
        self.sex_list = [{"name": "Unknown", "number": 0}, 
                    {"name": "Male", "number": 1},
                    {"name": "Female", "number":2}
                ]
        for item in self.sex_list:
            self.sex_combo.addItem(item["name"], userData=item["number"])
        
        self.phenotype_combo = QComboBox()  # case /control
        self.phenotype_list = [{"name": "Unknown", "number": 0}, 
                    {"name": "Unaffected", "number": 1},
                    {"name": "Affected", "number": 2}
                ]
        for item in self.phenotype_list:
            self.phenotype_combo.addItem(item["name"], userData=item["number"])

        self.view.addRow("Sex", self.sex_combo)
        self.view.addRow("Affected", self.phenotype_combo)
        
        main_layout = QVBoxLayout(self)
        main_layout.addLayout(self.view)
        main_layout.addStretch()

    def get_sample(self):

        sample = {
            "sex": self.sex_combo.currentData(),
            "phenotype": self.phenotype_combo.currentData()
        }

        return sample

    def set_sample(self, sample: dict):
        if "sex" in sample:
            self.sex_combo.setCurrentText(
                next(
                    (
                        item["name"]
                        for item in self.sex_list
                        if item["number"] == sample["sex"]
                    ),
                    "Unknown",
                )
            )

        if "phenotype" in sample:
            self.sex_combo.setCurrentText(
                next(
                    (
                        item["name"]
                        for item in self.phenotype_list
                        if item["number"] == sample["sex"]
                    ),
                    "No",
                )
            )


class HistorySectionWidget(AbstractSectionWidget):
    def __init__(self, parent: QWidget = None):
        super().__init__(parent)

        self.setWindowTitle("History")
        self.setToolTip("Modification history of current sample")

        self.view = DictWidget()
        self.view.view.horizontalHeader().hide()
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.view)
        main_layout.setContentsMargins(0, 0, 0, 0)

    def set_sample(self, sample: dict):

        results = {}

        for rec in sql.get_histories(self.conn, "samples", sample["id"]):

            key = rec["timestamp"]
            value = "{user} change {field} from {before} to {after}".format(**rec)
            results[key] = value

        self.view.set_dict(results)

    def get_sample(self) -> dict:
        return {}


class SampleWidget(QWidget):
    """A tab view with Strategy Pattern showing different view for the selected sample

    w = SampleWidget()
    w.load(id)
    w.save(id)

    """
    def __init__(self, conn: sqlite3.Connection, parent=None):
        super().__init__()

        self._conn = conn
        self._section_widgets = []

        self.tab_widget = QTabWidget()
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.tab_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.add_section(EvaluationSectionWidget())
        self.add_section(PhenotypeSectionWidget())
        self.add_section(HistorySectionWidget())

    def add_section(self, widget: AbstractSectionWidget):
        """Add tab section

        Args:
            widget (AbstractSectionWidget): All subclass of AbstractSectionWidget
        """
        widget.conn = self.conn
        self._section_widgets.append(widget)

        subw = QWidget()
        vbox = QVBoxLayout(subw)
        label = QLabel("{}".format(widget.toolTip()))
        vbox.addWidget(label)
        vbox.addWidget(widget)

        widget.windowTitleChanged.connect(self._on_section_name_changed)

        self.tab_widget.addTab(subw, widget.windowTitle())

    def _on_section_name_changed(self, text):

        index = self._section_widgets.index(self.sender())

        if index:
            self.tab_widget.setTabText(index, text)

    @property
    def conn(self):
        return self._conn

    @conn.setter
    def conn(self, c: sqlite3.Connection):
        self._conn = conn
        for widget in self._section_widgets:
            widget.conn = conn

    def save(self, sample_id: int):
        """Save widget forms to the database

        It also checks if another sqlite instance has changed data and trigger a messagebox if it is.

        Args:
            sample_id (int): sample sql id
        """

        sample = sql.get_sample(self.conn, sample_id)
        current_sample_hash = self.get_sample_hash(sample)

        if self.last_sample_hash != current_sample_hash:
            ret = QMessageBox.warning(
                None,
                "Database has been modified by another user.",
                "Do you want to overwrite value?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if ret == QMessageBox.No:
                return

        for widget in self._section_widgets:
            sample.update(widget.get_sample())

        sql.update_sample(self.conn, sample)

    def load(self, sample_id: int):
        """Load widget forms from database

        Args:
            sample_id (int): sample sql id
        """
        sample = sql.get_sample(self._conn, sample_id)
        self.last_sample_hash = self.get_sample_hash(sample)

        # # Set name
        name = "{name}".format(**sample)
        self.setWindowTitle("Sample edition: " + name)

        for widget in self._section_widgets:
            widget.set_sample(sample)

    def get_validation_from_data(self, data):
        return {
            "classif_index": int("{classification}".format(**data)),
            "tags": data["tags"],
            "comment": data["comment"],
        }

    def get_gui_state(self):
        """
        Used to identify if any writable value was changed by an user when closing the widget
        """
        values = []
        values.append(self.classification.currentIndex())
        values.append(self.tag_edit.text())
        values.append(self.comment.toPlainText())
        return values

    def get_sample_hash(self, sample: dict) -> str:
        """Return a footprint of a sample based on editable fields.

        This is used to check if sample has been changed by other before to save into the database

        Args:
            sample (dict): sample

        Returns:
            str: a string representation of a sample
        """
        return repr(
            {
                k: v
                for k, v in sample.items()
                if k in ["family, classification", "comment", "tags", "sex", "phenotype"]
            }
        )

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
    conn = sql.get_sql_connection("L:/Archives/NGS/BIO_INFO/BIO_INFO_Sam/scripts/cutevariant_project/devel_june2022.db")

    w = SampleDialog(conn, 1)

    w.show()

    app.exec_()
