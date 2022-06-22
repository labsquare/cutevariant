import sqlite3
import typing

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

from cutevariant.gui.widgets import MarkdownEditor
from cutevariant.core import sql
from cutevariant.core.report import SampleReport
from cutevariant.config import Config

from cutevariant.gui.ficon import FIcon

from cutevariant.gui.widgets import DictWidget, TagEdit
from cutevariant.gui.widgets.multi_combobox import MultiComboBox

from cutevariant.gui.widgets import ChoiceButton

from cutevariant import gui

import cutevariant.constants as cst
from cutevariant import commons as cm
from cutevariant.gui.formatters.cutestyle import CutestyleFormatter

from cutevariant.gui import tooltip as toolTip


LOCK_TOOLTIP_MESSAGE = "Genotype can't be edited because the sample is locked"

# TODO: move this function to commons functions?
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
        if hasattr(cst, "HAS_OPERATOR"):
            self.TAG_SEPARATOR = cst.HAS_OPERATOR
        else:
            self.TAG_SEPARATOR = ","
        self.setWindowTitle("Evaluation")
        self.setToolTip("You can edit sample information")
        main_layout = QFormLayout()

        self.name_label = QLabel()

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

        main_layout.addRow("Sample", self.name_label)
        main_layout.addRow("Classification", self.class_combo)
        main_layout.addRow("Tags", self.tag_layout)
        main_layout.addRow("Comment", self.comment)
        self.setLayout(main_layout)

        # Load classification
        config = Config("classifications")
        self.sample_classification = config.get("samples")
        self.sample_classification = sorted(self.sample_classification, key=lambda c: c["number"])
        for item in self.sample_classification:
            self.class_combo.addItem(
                FIcon(0xF012F, item.get("color", "gray")),
                item["name"],
                userData=item["number"],
            )

    def get_sample(self) -> dict:
        sample = {
            "name": self.name_label.text(),
            "classification": self.class_combo.currentData(),
            "tags": self.TAG_SEPARATOR.join(
                [tag.strip() for tag in self.tag_edit.text().split(",") if tag.strip()]
            ),
            "comment": self.comment.toPlainText(),
        }

        return sample

    def set_sample(self, sample: dict):

        # Load sample name
        if "name" in sample:
            self.name_label.setText(str(sample["name"]))

        # Load tags
        tags = []
        config = Config("tags")
        for tag in config.get("samples", []):
            tags.append(tag)
            self.tag_edit.addItem(tag.get("name", ""))
        self.tag_edit.setText(",".join(sample.get("tags", "").split(self.TAG_SEPARATOR)))

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

        if is_locked(self, sample["id"]):
            self.setToolTip(LOCK_TOOLTIP_MESSAGE)
            self.tag_edit.setDisabled(True)
            self.comment.preview_btn.setDisabled(True)


class PedigreeSectionWidget(AbstractSectionWidget):
    def __init__(self, parent: QWidget = None):
        super().__init__(parent)

        self.setWindowTitle("Pedigree")
        self.setToolTip("You can edit pedigree information")
        self.view = QFormLayout()

        # values based on https://gatk.broadinstitute.org/hc/en-us/articles/360035531972-PED-Pedigree-format

        # Family
        self.family_edit = QLineEdit()
        self.father_edit = QLineEdit()
        self.mother_edit = QLineEdit()

        # Add rows
        self.view.addRow("Family", self.family_edit)
        self.view.addRow("Father", self.father_edit)
        self.view.addRow("Mother", self.mother_edit)

        main_layout = QVBoxLayout(self)
        main_layout.addLayout(self.view)
        main_layout.addStretch()

    def get_sample(self):

        sample = {
            "family_id": self.family_edit.text(),
            "father_id": self.father_edit.text(),
            "mother_id": self.mother_edit.text(),
        }

        return sample

    def set_sample(self, sample: dict):

        # Load family
        if "family_id" in sample:
            self.family_edit.setText(str(sample["family_id"]))

        # Load father
        if "father_id" in sample:
            self.father_edit.setText(str(sample["father_id"]))

        # Load mother
        if "mother_id" in sample:
            self.mother_edit.setText(str(sample["mother_id"]))

        if is_locked(self, sample["id"]):
            self.setToolTip(LOCK_TOOLTIP_MESSAGE)
            # self.tag_edit.setReadOnly(True)
            self.family_edit.setDisabled(True)
            self.father_edit.setDisabled(True)
            self.mother_edit.setDisabled(True)


class PhenotypeSectionWidget(AbstractSectionWidget):
    def __init__(self, parent: QWidget = None):
        super().__init__(parent)

        self.setWindowTitle("Phenotype")
        self.setToolTip("You can edit phenotype information")
        self.view = QFormLayout()

        # values based on https://gatk.broadinstitute.org/hc/en-us/articles/360035531972-PED-Pedigree-format

        # Sex
        self.sex_combo = QComboBox()
        self.sex_list = [
            {"name": "Unknown", "number": 0},
            {"name": "Male", "number": 1},
            {"name": "Female", "number": 2},
        ]
        for item in self.sex_list:
            self.sex_combo.addItem(item["name"], userData=item["number"])

        # Phenotype
        self.phenotype_combo = QComboBox()  # case /control
        self.phenotype_list = [
            {"name": "Unknown", "number": 0},
            {"name": "Unaffected", "number": 1},
            {"name": "Affected", "number": 2},
        ]
        for item in self.phenotype_list:
            self.phenotype_combo.addItem(item["name"], userData=item["number"])

        # Add rows
        self.view.addRow("Sex", self.sex_combo)
        self.view.addRow("Affected", self.phenotype_combo)

        main_layout = QVBoxLayout(self)
        main_layout.addLayout(self.view)
        main_layout.addStretch()

    def get_sample(self):

        sample = {
            "sex": self.sex_combo.currentData(),
            "phenotype": self.phenotype_combo.currentData(),
        }

        return sample

    def set_sample(self, sample: dict):

        # Load sex
        if "sex" in sample:
            self.sex_combo.setCurrentText(
                next(
                    (item["name"] for item in self.sex_list if item["number"] == sample["sex"]),
                    "Unknown",
                )
            )

        # Load phenotype
        if "phenotype" in sample:
            self.phenotype_combo.setCurrentText(
                next(
                    (
                        item["name"]
                        for item in self.phenotype_list
                        if item["number"] == sample["phenotype"]
                    ),
                    "No",
                )
            )

        if is_locked(self, sample["id"]):
            self.setToolTip(LOCK_TOOLTIP_MESSAGE)
            # self.tag_edit.setReadOnly(True)
            self.sex_combo.setDisabled(True)
            self.phenotype_combo.setDisabled(True)


class OccurenceVerticalHeader(QHeaderView):
    # TODO
    def __init__(self, parent=None):
        super().__init__(Qt.Vertical, parent)

    def sizeHint(self):
        return QSize(30, super().sizeHint().height())

    def paintSection(self, painter: QPainter, rect: QRect, section: int):

        if painter is None:
            return

        painter.save()
        super().paintSection(painter, rect, section)

        number = self.model().variant(section)["classification"]

        painter.restore()


class OccurenceModel(QAbstractTableModel):

    VARIANT_COLUMN = 0
    CLASSIFICATION_COLUMN = 1

    def __init__(self, parent=None):
        super().__init__(parent)
        self._parent = parent
        self._items = []
        self._headers = ["variant", "classification"]

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent == QModelIndex():
            return len(self._items)

        return 0

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent == QModelIndex():
            return 2

        return 0

    def item(self, row: int):
        return self._items[row]

    def load(self, conn: sqlite3.Connection, sample_id: int):

        self.beginResetModel()
        self._items = []
        for item in sql.get_sample_variant_classification(conn, sample_id=sample_id):
            if "classification" in item:
                if item["classification"] > 0:
                    self._items.append(item)
        self.endResetModel()

    def data(self, index: QModelIndex, role: Qt.ItemDataRole) -> typing.Any:

        if not index.isValid():
            return None

        item = self.item(index.row())

        if role == Qt.DisplayRole:
            if index.column() == OccurenceModel.VARIANT_COLUMN:
                variant_id = item.get("variant_id", "error")
                variant_text = cm.find_variant_name(conn=self._parent.conn, variant_id=variant_id, troncate=False)
                return variant_text

            if index.column() == OccurenceModel.CLASSIFICATION_COLUMN:
                classification = item.get("classification", 0)
                classification_text = str(classification)
                config = Config("classifications")
                self.genotype_classification = config.get("genotypes")
                for item in self.genotype_classification:
                    if item["number"] == classification:
                        classification_text = item["name"]

                return classification_text

        if role == Qt.ToolTipRole:
            return self.create_tooltip(index.row())

    def headerData(self, section: int, orientation: Qt.Orientation, role) -> typing.Any:

        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self._headers[section]

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable

    def create_tooltip(self, row: int):
        """Return tooltip

        TODO:
            Get data from sql, not from memory

        Args:
            row (int): Description

        Returns:
            TYPE: Description
        """

        tooltip = toolTip.genotype_tooltip(data=self.item(row), conn=self._parent.conn)
        return tooltip


class OccurrenceSectionWidget(AbstractSectionWidget):

    WINDOW_TITLE_PREFIX = "Variants"

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)

        self.setWindowTitle(OccurrenceSectionWidget.WINDOW_TITLE_PREFIX)
        self.setToolTip("List of validated variants for the current sample")
        main_layout = QVBoxLayout(self)
        self.model = OccurenceModel(self)
        self.delegate = gui.FormatterDelegate()
        self.delegate.set_formatter(CutestyleFormatter())
        self.view = QTableView()
        self.view.setItemDelegate(self.delegate)
        self.view.setModel(self.model)
        self.view.horizontalHeader().hide()
        self.view.setAlternatingRowColors(True)

        self.view.verticalHeader().hide()
        self.view.setAlternatingRowColors(True)
        self.view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.view.setSelectionMode(QAbstractItemView.SingleSelection)
        self.view.setShowGrid(False)
        self.summary_label = QLabel()
        main_layout.addWidget(self.view)
        main_layout.addWidget(self.summary_label)
        main_layout.setContentsMargins(0, 0, 0, 0)

    # def set_variant(self, variant: dict):
    def set_sample(self, sample: dict):

        self.model.load(self.conn, sample["id"])
        self.view.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)

        count = self.model.rowCount()
        # total = len(list(sql.get_samples(self.conn)))
        total = len(list(sql.get_sample_variant_classification(self.conn, sample["id"])))

        self.setWindowTitle(OccurrenceSectionWidget.WINDOW_TITLE_PREFIX + f" ({count}/{total})")

        ## Get samples count

    def get_sample(self) -> dict:
        return {}


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

            key = rec["timestamp"] + " [" + str(rec["id"]) + "]"
            value = "{user} change {field} from '{before}' to '{after}'".format(**rec)
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
        self.add_section(PedigreeSectionWidget())
        self.add_section(PhenotypeSectionWidget())
        self.add_section(OccurrenceSectionWidget())
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
        name = "Sample edition - {name}".format(**sample)
        self.setWindowTitle(name)

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

        self._conn = conn
        self._sample_id = sample_id
        self.w = SampleWidget(conn)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        self.html_button = QPushButton(self.tr("Create report ..."))

        self.button_layout = QHBoxLayout()
        self.button_layout.addWidget(self.html_button)
        self.button_layout.addStretch()
        self.button_layout.addWidget(self.button_box)

        vLayout = QVBoxLayout(self)
        vLayout.addWidget(self.w)
        vLayout.addLayout(self.button_layout)

        self.load()

        self.button_box.accepted.connect(self.save)
        self.button_box.rejected.connect(self.reject)
        self.html_button.clicked.connect(self.export_report)

        # self.resize(800, 600)

    def load(self):
        self.w.load(self._sample_id)
        self.setWindowTitle(self.w.windowTitle())

    def save(self):
        self.w.save(self._sample_id)
        self.accept()

    def export_report(self):
        """Create HTML report"""

        # Get output file
        output, _ = QFileDialog.getSaveFileName(
            self, "File name", QDir.homePath(), self.tr("HTML (*.html)")
        )
        if not output:
            return

        if not output.endswith(".html"):
            output += ".html"

        # Get template
        config = Config("report")
        template = config.get("html_template", None)
        if not template:
            QMessageBox.warning(
                self, "No template defined", "Please configure a template from settings"
            )
            return

        # Create report
        report = SampleReport(self._conn, self._sample_id)
        report.set_template(template)
        report.create(output)

        ret = QMessageBox.question(
            self, "report", "Do you want to open the report ?", QMessageBox.Yes | QMessageBox.No
        )

        if ret == QMessageBox.Yes:
            QDesktopServices.openUrl(output)


if __name__ == "__main__":
    import sys
    from cutevariant.core import sql

    app = QApplication(sys.argv)

    # conn = sql.get_sql_connection("/home/sacha/exome/exome.db")
    conn = sql.get_sql_connection(
        "L:/Archives/NGS/BIO_INFO/BIO_INFO_Sam/scripts/cutevariant_project/devel_june2022.db"
    )

    w = SampleDialog(conn, 1)

    w.show()

    app.exec_()
