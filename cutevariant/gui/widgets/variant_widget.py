import sqlite3
import typing

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QTableView,
    QMainWindow,
    QVBoxLayout,
    QLineEdit,
)

from PySide6.QtCore import Qt, QSortFilterProxyModel, QAbstractTableModel
from cutevariant.gui.widgets import DictWidget, MarkdownEditor
from cutevariant.gui.widgets import TagEdit
from cutevariant.config import Config

from cutevariant import gui  # FormatterDelegate / cycle loop
from cutevariant.gui.ficon import FIcon
from cutevariant.gui.formatters.cutestyle import CutestyleFormatter
from cutevariant import constants as cst
from cutevariant import commons as cm
from cutevariant.gui import tooltip as toolTip

# from cutevariant.gui.formatters.cutestyle import CutestyleFormatter

from cutevariant.core import sql


class AbstractSectionWidget(QWidget):
    def __init__(self, parent: QWidget = None):
        super().__init__()

        self.conn = None

    def set_variant(self, variant: dict):
        raise NotImplementedError

    def get_variant(self) -> dict:
        raise NotImplementedError


class EvaluationSectionWidget(AbstractSectionWidget):
    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        if hasattr(cst, "HAS_OPERATOR"):
            self.TAG_SEPARATOR = cst.HAS_OPERATOR
        else:
            self.TAG_SEPARATOR = ","
        self.setWindowTitle("Evaluation")
        self.setToolTip("You can edit variant information")
        main_layout = QFormLayout()

        self.variant_label = QLabel()

        self.favorite = QCheckBox()
        self.favorite.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        self.favorite.setText(self.tr("Mark variant as favorite"))

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

        main_layout.addRow("Variant", self.variant_label)
        main_layout.addRow("Favorite", self.favorite)
        main_layout.addRow("Classification", self.class_combo)
        main_layout.addRow("Tags", self.tag_layout)
        main_layout.addRow("Comment", self.comment)
        self.setLayout(main_layout)

        # Load classification
        config = Config("classifications")
        self.variant_classification = config.get("variants")
        for item in self.variant_classification:
            self.class_combo.addItem(
                FIcon(0xF012F, item.get("color", "gray")),
                item["name"],
                userData=item["number"],
            )

    def get_variant(self) -> dict:
        variant = {
            # "id": self.variant_label.text(),
            "favorite": self.favorite.isChecked(),
            "classification": self.class_combo.currentData(),
            "tags": self.TAG_SEPARATOR.join(
                [tag for tag in self.tag_edit.text().split(",") if tag]
            ),
            "comment": self.comment.toPlainText(),
        }

        return variant

    def set_variant(self, variant: dict):

        # Load variant
        if "id" in variant:
            # find variant name
            variant_id = variant["id"]
            variant_text = cm.find_variant_name(conn=self.conn, variant_id=variant_id, troncate=False)
            self.variant_label.setText(variant_text)

        # Load favorite
        if "favorite" in variant:
            # Bug with pyside.. need to cast int
            self.favorite.setCheckState(Qt.Checked if variant["favorite"] == 1 else Qt.Unchecked)

        # Load tags      
        tags = []
        config = Config("tags")
        for tag in config.get("variants", []):
            tags.append(tag)
            self.tag_edit.addItem(tag.get("name",""))
        self.tag_edit.setText(",".join(variant.get("tags", "").split(self.TAG_SEPARATOR)))
            
        # Load comment
        if "comment" in variant:
            self.comment.setPlainText(variant["comment"])
            self.comment.preview_btn.setChecked(True)

        # Load classification
        if "classification" in variant:
            self.class_combo.setCurrentText(
                next(
                    (
                        item["name"]
                        for item in self.variant_classification
                        if item["number"] == variant["classification"]
                    ),
                    "Unknown",
                )
            )


class VariantSectionWidget(AbstractSectionWidget):
    def __init__(self, parent: QWidget = None):
        super().__init__(parent)

        self.setWindowTitle("Variants")
        self.setToolTip("Annotation of the current variant")
        self.view = DictWidget()
        self.view.view.horizontalHeader().hide()
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.view)

    def set_variant(self, variant: dict):

        self.view.set_dict(
            {i: v for i, v in variant.items() if i not in ["annotations", "samples"]}
        )

        # self.view.view.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.view.view.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.view.view.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)

    def get_variant(self):
        return {}


class AnnotationsSectionWidget(AbstractSectionWidget):
    def __init__(self, parent: QWidget = None):
        super().__init__(parent)

        self.variant = {}
        self.setWindowTitle("Annotations")
        self.setToolTip("Annotation of the current variant for a specific transcript")
        self.view = DictWidget()
        self.view.view.horizontalHeader().hide()
        self.ann_combo = QComboBox()
        self.ann_combo.currentIndexChanged.connect(self.load_annotation)

        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.ann_combo)
        main_layout.addWidget(self.view)

    def set_variant(self, variant: dict):
        self.variant = variant
        self.ann_combo.clear()
        if "annotations" in variant:
            for i, val in enumerate(variant["annotations"]):
                if "transcript" in val:
                    self.ann_combo.addItem(val["transcript"], userData=val)
                else:
                    self.ann_combo.addItem(f"Annotation {i}", userData=val)

        self.view.view.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)

    def get_variant(self) -> dict:
        return {}

    def load_annotation(self):

        current = self.ann_combo.currentIndex()
        if "annotations" in self.variant:
            adata = self.variant["annotations"][current]
            self.view.set_dict({i: k for i, k in adata.items() if k != ""})


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

        # try:
        #     classification = next(i for i in self.model().classifications if i["number"] == number)

        #     color = classification.get("color")
        #     icon = 0xF0130

        #     icon_favorite = 0xF0133

        #     pen = QPen(QColor(classification.get("color")))
        #     pen.setWidth(6)
        #     painter.setPen(pen)
        #     painter.setBrush(QBrush(classification.get("color")))
        #     painter.drawLine(rect.left(), rect.top() + 1, rect.left(), rect.bottom() - 1)

        #     target = QRect(0, 0, 20, 20)
        #     pix = FIcon(icon_favorite if favorite else icon, color).pixmap(target.size())
        #     target.moveCenter(rect.center() + QPoint(1, 1))

        #     painter.drawPixmap(target, pix)

        # except Exception as e:
        #     LOGGER.debug("Cannot draw classification: " + str(e))


class OccurenceModel(QAbstractTableModel):

    NAME_COLUMN = 0
    CLASSIFICATION_COLUMN = 2
    GENOTYPE_COLUMN = 1

    def __init__(self, parent=None, validated: bool = False):
        super().__init__(parent)
        self._parent = parent
        self._items = []
        self._validated = validated
        self._headers = ["sample", "gt", "classification"]

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent == QModelIndex():
            return len(self._items)

        return 0

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent == QModelIndex():
            return 3

        return 0

    def item(self, row: int):
        return self._items[row]

    def load(self, conn: sqlite3.Connection, variant_id: int):

        self.beginResetModel()
        if self._validated:
            self._items = []
            for item in sql.get_sample_variant_classification(conn, variant_id=variant_id):
                if "classification" in item:
                    if item["classification"] > 0:
                        self._items.append(item)
        else:
            self._items = list(sql.get_variant_occurences(conn, variant_id))
        # sort (revert) by classification number
        self._items = sorted(self._items, key=lambda c: c["classification"], reverse=True)

        self.endResetModel()

    def data(self, index: QModelIndex, role: Qt.ItemDataRole) -> typing.Any:

        if not index.isValid():
            return None

        item = self.item(index.row())

        if role == Qt.DisplayRole:

            if index.column() == OccurenceModel.NAME_COLUMN:
                sample_name = item.get("name", "error")
                return sample_name

            if index.column() == OccurenceModel.CLASSIFICATION_COLUMN:
                classification = item.get("classification", 0)
                classification_text = str(classification)
                config = Config("classifications")
                self.genotype_classification = config.get("genotypes")
                for item in self.genotype_classification:
                    if item["number"] == classification:
                        classification_text = item["name"]
                return classification_text

            if index.column() == OccurenceModel.GENOTYPE_COLUMN:
                return item.get("gt", -1)

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

    WINDOW_TITLE_PREFIX_OCCURENCE = "Occurence"
    WINDOW_TITLE_PREFIX_VALIDATED = "Variant Validation"

    def __init__(self, parent: QWidget = None, validated: bool = False):
        super().__init__(parent)

        if validated:
            self.windowTitlePrefix = OccurrenceSectionWidget.WINDOW_TITLE_PREFIX_VALIDATED
        else:
            self.windowTitlePrefix = OccurrenceSectionWidget.WINDOW_TITLE_PREFIX_OCCURENCE

        # self.setWindowTitle(OccurrenceSectionWidget.WINDOW_TITLE_PREFIX)
        self.setWindowTitle(self.windowTitlePrefix)
        self.setToolTip("List of all samples where the current variant belong to")
        main_layout = QVBoxLayout(self)
        self.model = OccurenceModel(self, validated=validated)
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

    def set_variant(self, variant: dict):

        self.model.load(self.conn, variant["id"])
        self.view.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)

        count = self.model.rowCount()
        total = len(list(sql.get_samples(self.conn)))

        self.setWindowTitle(
            # OccurrenceSectionWidget.WINDOW_TITLE_PREFIX + f" ({count}/{total})"
            self.windowTitlePrefix
            + f" ({count}/{total})"
        )

        ## Get samples count

    def get_variant(self) -> dict:
        return {}


class HistorySectionWidget(AbstractSectionWidget):
    def __init__(self, parent: QWidget = None):
        super().__init__(parent)

        self.setWindowTitle("History")
        self.setToolTip("Modification history of the current variant")

        self.view = DictWidget()
        self.view.view.horizontalHeader().hide()
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.view)
        main_layout.setContentsMargins(0, 0, 0, 0)

    def set_variant(self, variant: dict):

        results = {}

        for rec in sql.get_histories(self.conn, "variants", variant["id"]):

            key = rec["timestamp"] + " [" + str(rec["id"]) + "]"
            value = "{user} change {field} from {before} to {after}".format(**rec)
            results[key] = value

        self.view.set_dict(results)

    def get_variant(self) -> dict:
        return {}


class VariantWidget(QWidget):

    """A tab view with Strategy Pattern showing different view for the selected variant

    w = VariantWidget()
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
        self.add_section(VariantSectionWidget())
        self.add_section(AnnotationsSectionWidget())
        self.add_section(OccurrenceSectionWidget())
        # self.add_section(OccurrenceSectionWidget(validated=True)) # depreciated
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
        # vbox.setContentsMargins(0, 0, 0, 0)

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

    def save(self, variant_id: int):
        """Save widget forms to the database

        It also checks if another sqlite instance has changed data and trigger a messagebox if it is.

        Args:
            variant_id (int): variant sql id
        """

        variant = sql.get_variant(self.conn, variant_id, with_annotations=True, with_samples=True)
        current_variant_hash = self.get_variant_hash(variant)

        if self.last_variant_hash != current_variant_hash:
            ret = QMessageBox.warning(
                None,
                "Database has been modified by another user.",
                "Do you want to overwrite value?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if ret == QMessageBox.No:
                return

        del variant["annotations"]
        del variant["samples"]

        for widget in self._section_widgets:
            variant.update(widget.get_variant())

        sql.update_variant(self.conn, variant)

    def load(self, variant_id: int):
        """Load widget forms from database

        Args:
            variant_id (int): variant sql id
        """
        variant = sql.get_variant(self._conn, variant_id, with_annotations=True, with_samples=True)
        self.last_variant_hash = self.get_variant_hash(variant)

        variant_name = cm.find_variant_name(conn=self.conn, variant_id=variant_id, troncate=True)

        self.setWindowTitle(f"Variant edition - {variant_name}")

        for widget in self._section_widgets:
            widget.set_variant(variant)

    def get_validation_from_data(self, data):
        return {
            "favorite": data["favorite"],
            "classif_index": int("{classification}".format(**data)),
            "tags": data["tags"],
            "comment": data["comment"],
        }

    def get_gui_state(self):
        """
        Used to identify if any writable value was changed by an user when closing the widget
        """
        values = []
        values.append(self.favorite.isChecked())
        values.append(self.classification.currentIndex())
        values.append(self.tag_edit.text())
        values.append(self.comment.toPlainText())
        return values

    def get_variant_hash(self, variant: dict) -> str:
        """Return a footprint of a variant based on editable fields.

        This is used to check if variant has been changed by other before to save into the database

        Args:
            variant (dict): variant

        Returns:
            str: a string representation of a variant
        """
        return repr(
            {
                k: v
                for k, v in variant.items()
                if k in ["classification", "favorite", "comment", "tags"]
            }
        )


class VariantDialog(QDialog):
    def __init__(self, conn, variant_id, parent=None):
        super().__init__(parent)

        self.variant_id = variant_id
        self.w = VariantWidget(conn)
        self.button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        vLayout = QVBoxLayout(self)
        vLayout.addWidget(self.w)
        vLayout.addWidget(self.button_box)

        self.button_box.accepted.connect(self.save)
        self.button_box.rejected.connect(self.reject)

        # self.resize(800, 600)

        self.load()
        self.setWindowTitle(self.w.windowTitle())

    def load(self):
        self.w.load(self.variant_id)

    def save(self):
        self.w.save(self.variant_id)
        self.accept()


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    conn = sql.get_sql_connection("/home/sacha/test.db")
    # conn = sql.get_sql_connection("C:/Users/Ichtyornis/Projects/cutevariant/test2.db")
    w = VariantDialog(conn, 1)

    w.show()

    app.exec()
