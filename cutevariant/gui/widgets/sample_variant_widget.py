import sqlite3
from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

from cutevariant.config import Config
from cutevariant import commons as cm
from cutevariant.core import sql
from cutevariant.gui.ficon import FIcon
from cutevariant.gui.widgets import DictWidget, MarkdownEditor, TagEdit

from cutevariant import constants, LOGGER


class QHLine(QFrame):
    def __init__(self):
        super(QHLine, self).__init__()
        self.setFrameShape(QFrame.HLine)
        self.setFrameShadow(QFrame.Sunken)


class AbstractSectionWidget(QWidget):
    def __init__(self, parent: QWidget = None):
        super().__init__()

        self.conn = None

    def set_genotype(self, variant: dict):
        raise NotImplementedError

    def get_genotype(self) -> dict:
        raise NotImplementedError


class GenotypeSectionWidget(AbstractSectionWidget):
    def __init__(self, parent: QWidget = None):
        super().__init__(parent)

        self.setWindowTitle("Genotype")
        self.setToolTip("Fields attached to the current genotype")
        self.view = DictWidget()
        self.view.view.horizontalHeader().hide()
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.view)

    def set_genotype(self, genotype: dict):

        self.view.set_dict(genotype)

        self.view.view.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.view.view.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)

    def get_genotype(self):
        return {}


class EvaluationSectionWidget(AbstractSectionWidget):
    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        if hasattr(constants, "HAS_OPERATOR"):
            self.TAG_SEPARATOR = constants.HAS_OPERATOR
        else:
            self.TAG_SEPARATOR = ","
        self.setWindowTitle("Evaluation")
        self.setToolTip("Edit genotype information here")
        main_layout = QFormLayout()

        self.sample_label = QLabel()
        self.variant_label = QLabel()

        self.class_combo = QComboBox()
        self.tag_edit = TagEdit()
        self.tag_edit.setPlaceholderText(self.tr("Tag separated by comma..."))
        self.tag_layout = QHBoxLayout()
        self.tag_layout.setContentsMargins(0, 0, 0, 0)
        self.tag_layout.addWidget(self.tag_edit)

        self.edit_comment_btn = QPushButton("Edit comment")
        self.edit_comment_btn.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Minimum)

        self.comment = MarkdownEditor()
        self.comment.preview_btn.setText("Preview/Edit comment")

        main_layout.addRow("Sample", self.sample_label)
        main_layout.addRow("Variant", self.variant_label)
        main_layout.addRow("Classification", self.class_combo)
        main_layout.addRow("Tags", self.tag_layout)
        main_layout.addRow("Comment", self.comment)
        self.setLayout(main_layout)

        # Load classification
        config = Config("classifications")
        self.genotype_classification = config.get("genotypes")
        self.genotype_classification = sorted(
            self.genotype_classification, key=lambda c: c["number"]
        )
        for item in self.genotype_classification:
            self.class_combo.addItem(
                FIcon(0xF012F, item.get("color", "gray")),
                item["name"],
                userData=item["number"],
            )

    def get_genotype(self) -> dict:
        genotype = {
            "classification": self.class_combo.currentData(),
            "tags": self.TAG_SEPARATOR.join(
                [tag.strip() for tag in self.tag_edit.text().split(",") if tag.strip()]
            ),
            "comment": self.comment.toPlainText(),
        }

        return genotype

    def set_genotype(self, genotype: dict):

        # Load Sample name
        sample = sql.get_sample(self.conn, genotype.get("sample_id", 0))
        # sample_name = sample.get("name", None)
        if "name" in sample:
            self.sample_label.setText(str(sample["name"]))

        # Load variant
        variant_id = genotype.get("variant_id", 0)
        variant_name = cm.find_variant_name(conn=self.conn, variant_id=variant_id, troncate=False)
        self.variant_label.setText(variant_name)

        # Load tags
        tags = []
        config = Config("tags")
        for tag in config.get("genotypes", []):
            tags.append(tag)
            self.tag_edit.addItem(tag.get("name",""))
        self.tag_edit.setText(",".join(genotype.get("tags", "").split(self.TAG_SEPARATOR)))

        # Load comment
        if "comment" in genotype:
            self.comment.setPlainText(genotype["comment"])
            self.comment.preview_btn.setChecked(True)

        # Load classification
        if "classification" in genotype:
            self.class_combo.setCurrentText(
                next(
                    (
                        item["name"]
                        for item in self.genotype_classification
                        if item["number"] == genotype["classification"]
                    ),
                    "Unknown",
                )
            )

        if self.is_locked(genotype["sample_id"]):
            self.setToolTip("Genotype can't be edited because the sample is locked")
            self.tag_edit.setDisabled(True)
            self.comment.preview_btn.setDisabled(True)
            self.class_combo.setDisabled(True)

    def is_locked(self, sample_id: int):
        """Prevents editing genotype if sample is classified as locked
        A sample is considered locked if its classification has the boolean "lock: true" set in the Config (yml) file.

        Args:
            sample_id (int): sql sample id

        Returns:
            locked (bool) : lock status of sample attached to current genotype
        """
        config_classif = Config("classifications").get("samples", None)
        sample = sql.get_sample(self.conn, sample_id)
        sample_classif = sample.get("classification", None)

        if config_classif == None or sample_classif == None:
            return False

        locked = False
        for config in config_classif:
            if config["number"] == sample_classif and "lock" in config:
                if config["lock"] == True:
                    locked = True
        return locked


class VariantSectionWidget(AbstractSectionWidget):
    def __init__(self, parent: QWidget = None):
        super().__init__(parent)

        self.setWindowTitle("Variant")
        self.setToolTip("Annotation of the current variant")
        self.view = DictWidget()
        self.view.view.horizontalHeader().hide()
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.view)

    def set_genotype(self, genotype: dict):

        variant = sql.get_variant(self.conn, genotype["variant_id"], with_annotations=False)

        self.view.set_dict(
            {i: v for i, v in variant.items() if i not in ["variant_id", "annotations", "samples"]}
        )

        self.view.view.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.view.view.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)

    def get_genotype(self):
        return {}


class SampleSectionWidget(AbstractSectionWidget):
    def __init__(self, parent: QWidget = None):
        super().__init__(parent)

        self.setWindowTitle("Sample")
        self.setToolTip("Annotation of the current sample")
        self.view = DictWidget()
        self.view.view.horizontalHeader().hide()
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.view)

    def set_genotype(self, genotype: dict):

        sample = sql.get_sample(self.conn, genotype["sample_id"])

        self.view.set_dict({i: v for i, v in sample.items() if i not in ["sample_id"]})

        self.view.view.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.view.view.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)

    def get_genotype(self):
        return {}


class HistorySectionWidget(AbstractSectionWidget):
    def __init__(self, parent: QWidget = None):
        super().__init__(parent)

        self.setWindowTitle("History")
        self.setToolTip("Modification history of current genotype")

        self.view = DictWidget()
        self.view.view.horizontalHeader().hide()
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.view)
        main_layout.setContentsMargins(0, 0, 0, 0)

    def set_genotype(self, genotype: dict):

        results = {}
        row_id = sql.get_genotype_rowid(self.conn, genotype["variant_id"], genotype["sample_id"])

        for rec in sql.get_histories(self.conn, "genotypes", row_id):

            key = rec["timestamp"] + " [" + str(rec["id"]) + "]"
            value = "{user} change {field} from '{before}' to '{after}'".format(**rec)
            results[key] = value

        self.view.set_dict(results)

    def get_genotype(self) -> dict:
        return {}


class SampleVariantWidget(QWidget):
    """A tab view with Strategy Pattern showing different views for the selected genotype

    w = SampleVariantWidget()
    w.load(sample_id, variant_id)
    w.save(sample_id, variant_id)

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
        self.add_section(GenotypeSectionWidget())
        self.add_section(VariantSectionWidget())
        self.add_section(SampleSectionWidget())
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

    def get_genotype(self, sample_id: int, variant_id: int):
        """Get dict representing selected row from "genotypes" table

        Args:
            sample_id (int): sql sample id
            variant_id (int): sql variant id

        Returns:
            genotype (dict): all fields from "genotypes" table corresponding to sample_id and variant_id
        """
        sample = sql.get_sample(self._conn, sample_id)
        fields = sql.get_table_columns(self._conn, "genotypes")
        genotype = [
            g
            for g in sql.get_genotypes(
                self.conn, variant_id, fields=fields, samples=[sample["name"]]
            )
        ]
        if len(genotype) > 1:
            LOGGER.error(
                f"Multiple genotypes returned for variant_id:{variant_id} with sample_id:{sample_id}"
            )
            return None
        # sql.get_genotypes keeps in output every field that was in samples={sample}
        # If not removed, sql.update_genotype will crash because they don't exist in "genotypes" table
        genotype[0].pop("name", None)
        return genotype[0]

    def save(self, sample_id: int, variant_id: int):
        """Save widget forms to the database

        It also checks if another sqlite instance has changed data and trigger a messagebox if it is.

        Args:
            sample_id (int): sample sql id
        """

        genotype = self.get_genotype(sample_id, variant_id)
        current_genotype_hash = self.get_genotype_hash(genotype)

        if self.last_genotype_hash != current_genotype_hash:
            ret = QMessageBox.warning(
                None,
                "Database has been modified by another user.",
                "Do you want to overwrite value?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if ret == QMessageBox.No:
                return

        for widget in self._section_widgets:
            genotype.update(widget.get_genotype())

        sql.update_genotypes(self.conn, genotype)

    def load(self, sample_id: int, variant_id: int):
        """Load widget forms from database

        Args:
            sample_id (int): sample sql id
        """
        genotype = self.get_genotype(sample_id, variant_id)
        self.last_genotype_hash = self.get_genotype_hash(genotype)
        sample = sql.get_sample(self.conn, genotype.get("sample_id", 0))
        sample_name = sample.get("name", "unknown")
        variant_name = cm.find_variant_name(conn=self.conn, variant_id=variant_id, troncate=True)
        self.setWindowTitle(f"Genotype edition - {sample_name} - {variant_name}")

        for widget in self._section_widgets:
            widget.set_genotype(genotype)

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

    def get_genotype_hash(self, sample: dict) -> str:
        """Return a footprint of a sample based on editable fields.

        This is used to check if sample has been changed by other before to save into the database

        Args:
            sample (dict): sample

        Returns:
            str: a string representation of a sample
        """
        return repr({k: v for k, v in sample.items() if k in ["classification", "comment", "tags"]})


class SampleVariantDialog(QDialog):
    def __init__(self, conn, sample_id, variant_id, parent=None):
        super().__init__()

        self.sample_id = sample_id
        self.variant_id = variant_id

        self.w = SampleVariantWidget(conn)
        self.button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        vLayout = QVBoxLayout(self)
        vLayout.addWidget(self.w)
        vLayout.addWidget(self.button_box)

        self.load()

        self.button_box.accepted.connect(self.save)
        self.button_box.rejected.connect(self.reject)

        # self.resize(800, 600)

    def load(self):
        self.w.load(self.sample_id, self.variant_id)
        self.setWindowTitle(self.w.windowTitle())

    def save(self):
        self.w.save(self.sample_id, self.variant_id)
        self.accept()


if __name__ == "__main__":
    import sys
    from cutevariant.core import sql

    app = QApplication(sys.argv)

    conn = sql.get_sql_connection(
        "L:/Archives/NGS/BIO_INFO/BIO_INFO_Sam/scripts/cutevariant_project/devel_7june2022.db"
    )

    w = SampleVariantDialog(conn, 1, 7)

    w.show()

    app.exec_()
