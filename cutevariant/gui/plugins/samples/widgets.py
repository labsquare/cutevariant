from logging import Logger
import sqlite3
import functools
from typing import List

from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtWidgets import *


from cutevariant import LOGGER
from cutevariant import constants as cst
from cutevariant.core import sql
from cutevariant.config import Config
from cutevariant.gui import plugin, style, MainWindow
from cutevariant.gui.widgets import SampleDialog
from cutevariant.gui.widgets import SamplesEditor
from cutevariant.gui import FIcon
from cutevariant.gui import tooltip as toolTip

import time

DEFAULT_SELECTION_NAME = cst.DEFAULT_SELECTION_NAME or "variants"
SAMPLES_SELECTION_NAME = cst.SAMPLES_SELECTION_NAME or "samples"
CURRENT_SAMPLE_SELECTION_NAME = cst.CURRENT_SAMPLE_SELECTION_NAME or "current_sample"
LOCKED_SELECTIONS = [DEFAULT_SELECTION_NAME, SAMPLES_SELECTION_NAME, CURRENT_SAMPLE_SELECTION_NAME]


class SampleModel(QAbstractTableModel):

    """Contains current samples"""

    NAME_COLUMN = 0
    PHENOTYPE_COLUMN = 1
    SEX_COLUMN = 2
    COMMENT_COLUMN = 3

    def __init__(self, conn: sqlite3.Connection = None):
        super().__init__()

        # real Model data samples
        self._samples = []

        # Samples to loads
        self._selected_samples = []
        self.conn = conn
        self.classifications = []

    def clear(self):
        self.beginResetModel()
        self._selected_samples.clear()
        self._samples.clear()
        self.endResetModel()

    def load(self):
        """Loads all the samples from the database"""
        if self.conn:
            self.beginResetModel()
            self._samples.clear()
            for sample in sql.get_samples(self.conn):
                if sample["name"] in self._selected_samples:
                    self._samples.append(sample)
            self.endResetModel()

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole):
        # Titles
        if orientation == Qt.Horizontal and role == Qt.DisplayRole and section == 0:
            return self.tr("Samples")

        # vertical header
        if role == Qt.ToolTipRole and orientation == Qt.Vertical:
            sample = self._samples[section]
            sample_tooltip = self.get_tooltip(section)
            return sample_tooltip

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):

        col = index.column()

        if role == Qt.DisplayRole:
            sample = self._samples[index.row()]
            if col == SampleModel.NAME_COLUMN:
                return sample.get("name", "unknown")

            if col == SampleModel.COMMENT_COLUMN:
                count_validation_positive_variant = sample.get(
                    "count_validation_positive_variant", 0
                )
                if count_validation_positive_variant == 0:
                    count_validation_positive_variant = ""
                return count_validation_positive_variant

        if role == Qt.DecorationRole:
            sample = self._samples[index.row()]
            color = QApplication.palette().color(QPalette.Text)
            color_alpha = QColor(QApplication.palette().color(QPalette.Text))
            color_alpha.setAlpha(50)

            if col == SampleModel.SEX_COLUMN:
                sex = sample.get("sex", None)
                if sex == 1:
                    return QIcon(FIcon(0xF029D))
                if sex == 2:
                    return QIcon(FIcon(0xF029C))
                if sex == 0:
                    return QIcon(FIcon(0xF029E, color_alpha))

            if col == SampleModel.PHENOTYPE_COLUMN:
                phenotype = sample.get("phenotype")
                if phenotype == 2:
                    col = QApplication.style().colors().get("red", "red")
                    return QIcon(FIcon(0xF08C9, QColor(col)))
                if phenotype == 1:
                    col = QApplication.style().colors().get("green", "red")
                    return QIcon(FIcon(0xF05DD, QColor(col)))

                return QIcon(FIcon(0xF001A, color_alpha))

            if col == SampleModel.COMMENT_COLUMN:
                comment = sample.get("comment", None)
                count_validation_positive_variant = sample.get(
                    "count_validation_positive_variant", 0
                )
                if count_validation_positive_variant:
                    # return QIcon(FIcon(0xF017F, color))
                    return QIcon(FIcon(0xF017A, color))
                if comment:
                    return QIcon(FIcon(0xF017A, color))

                return QIcon(FIcon(0xF017A, color_alpha))

        if role == Qt.ToolTipRole:

            sample = self._samples[index.row()]

            if col == SampleModel.COMMENT_COLUMN:
                sample_comment_tooltip = sample.get("comment", "").replace("\n", "<br>")
                return sample_comment_tooltip

            if col == SampleModel.NAME_COLUMN:
                sample_name_tooltip = self.get_tooltip(index.row())
                return sample_name_tooltip

            if col == SampleModel.PHENOTYPE_COLUMN:
                return cst.PHENOTYPE_DESC.get(int(sample["phenotype"]), "Unknown")

            if col == SampleModel.SEX_COLUMN:
                return cst.SEX_DESC.get(int(sample["sex"]), "Unknown")

    def get_tooltip(self, row: int) -> str:
        """Return all samples info as a formatted text"""

        tooltip = toolTip.sample_tooltip(data=self._samples[row], conn=self.conn)
        return tooltip

    def get_sample(self, row: int):
        if row >= 0 and row < len(self._samples):
            return self._samples[row]

    def set_samples(self, samples: list):
        self._selected_samples = samples
        self.load()

    def get_samples(self) -> list:
        return [i["name"] for i in self._samples]

    def add_samples(self, samples: list):
        self._selected_samples.extend(samples)
        self.load()

    def rowCount(self, index: QModelIndex = QModelIndex()) -> int:
        """override"""
        if index == QModelIndex():
            return len(self._samples)
        else:
            return 0

    def columnCount(self, index: QModelIndex = QModelIndex()) -> int:
        """override"""
        if index == QModelIndex():
            return 4
        else:
            return 0

    def update_sample(self, row: int, update_data: dict):
        """Update sample

        Args:
            row (int):
            update_data (dict):
        """
        self._samples[row].update(update_data)
        data = self.get_sample(row)
        sql.update_sample(self.conn, data)

        # find index
        left = self.index(row, 0)
        right = self.index(row, self.columnCount() - 1)
        if left.isValid() and right.isValid():
            LOGGER.debug("UPDATE INDEX " + str(left) + " " + str(right))
            self.dataChanged.emit(left, right)
            self.headerDataChanged.emit(Qt.Horizontal, left, right)

    def remove_samples(self, rows: list):

        rows = sorted(rows, reverse=True)
        self.beginResetModel()
        for row in rows:
            name = self._samples[row]["name"]
            self._selected_samples.remove(name)
            del self._samples[row]

        self.endResetModel()


class SampleVerticalHeader(QHeaderView):

    """Customize Vertical header with icons"""

    def __init__(self, parent=None):
        super().__init__(Qt.Vertical, parent)

    def sizeHint(self) -> QSize:
        """override"""
        return QSize(30, super().sizeHint().height())

    def paintSection(self, painter: QPainter, rect: QRect, section: int):

        if painter is None:
            return

        painter.save()
        super().paintSection(painter, rect, section)
        try:
            classification = self.model().get_sample(section).get("classification", 0)
            name = self.model().get_sample(section).get("name", None)

            painter.restore()

            style = next(i for i in self.model().classifications if i["number"] == classification)
            color = style.get("color", "white")
            # selected_samples = self.mainwindow.get_state_data("selected_samples") or []
            # if name in selected_samples:
            #     icon = 0xF0133
            # else:
            # icon = 0xF012F # or 0xF0009 or 0xF0B55
            icon = 0xF0009

            pen = QPen(QColor(color))
            pen.setWidth(6)
            painter.setPen(pen)
            painter.setBrush(QBrush(color))
            painter.drawLine(rect.left(), rect.top() + 1, rect.left(), rect.bottom() - 1)

            target = QRect(0, 0, 20, 20)
            pix = FIcon(icon, color).pixmap(target.size())
            target.moveCenter(rect.center() + QPoint(1, 1))

            painter.drawPixmap(target, pix)

        except Exception as e:
            LOGGER.debug("Cannot paint classification " + str(e))


class SamplesWidget(plugin.PluginWidget):

    LOCATION = plugin.DOCK_LOCATION
    ENABLE = True
    REFRESH_STATE_DATA = {"samples"}

    def __init__(self, parent=None):
        super().__init__(parent)

        self.tool_bar = QToolBar()
        self.tool_bar.setIconSize(QSize(16, 16))
        self.add_button = QPushButton(self.tr("Add sample(s)"))
        self.add_button.clicked.connect(self.on_add_samples)
        # Empty widget
        self.empty_widget = QWidget()
        self.empty_widget.setBackgroundRole(QPalette.Base)
        self.empty_widget.setAutoFillBackground(True)
        empty_layout = QVBoxLayout(self.empty_widget)
        empty_layout.setAlignment(Qt.AlignCenter)
        empty_layout.addWidget(self.add_button)

        self.setWindowIcon(FIcon(0xF000E))
        self.setWindowTitle(self.tr("Samples"))

        self.model = SampleModel(self.conn)

        self.view = QTableView()
        self.view.setModel(self.model)
        self.view.horizontalHeader().hide()
        self.view.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.view.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.view.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.view.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.view.setShowGrid(False)
        self.view.setSelectionMode(QAbstractItemView.SingleSelection)
        self.view.setSelectionBehavior(QAbstractItemView.SelectRows)
        
        self.view.setVerticalHeader(SampleVerticalHeader(parent))
        self.view.verticalHeader().setSectionsClickable(True)
        self.view.verticalHeader().sectionDoubleClicked.connect(self.on_double_clicked_vertical_header)

        self.view.doubleClicked.connect(self.on_double_clicked) 

        # Setup actions
        self._setup_actions()

        # Build layout
        self.stack_layout = QStackedLayout()
        self.stack_layout.addWidget(self.empty_widget)
        self.stack_layout.addWidget(self.view)
        self.stack_layout.setCurrentIndex(1)

        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.tool_bar)
        main_layout.addLayout(self.stack_layout)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

    def on_model_changed(self):

        if self.model.rowCount() > 0:
            self.stack_layout.setCurrentIndex(1)
        else:
            self.stack_layout.setCurrentIndex(0)

        self.mainwindow.set_state_data("samples", copy.deepcopy(self.model.get_samples()))

        # Automatically create source on all samples
        # self.on_create_samples_source(source_name="samples")

        # self.mainwindow.set_state_data("source", "samples")
        # self.mainwindow.refresh_plugins(sender=self)

    def on_add_samples(self):

        dialog = SamplesEditor(self.model.conn)

        if dialog.exec() == QDialog.Accepted:
            self.model.add_samples(dialog.get_selected_samples())
            self.on_model_changed()

            # TODO : QMessagebox
            # ret = QMessageBox.question(
            #     self,
            #     "Create new source",
            #     "Would you like to create a new source from selected samples ? If you answer no, you can always do it later",
            #     QMessageBox.Yes | QMessageBox.No,
            # )

            # if ret == QMessageBox.Yes:
            self.remove_all_sample_fields()
            self.on_create_samples_source(source_name=SAMPLES_SELECTION_NAME)

    def _create_classification_menu(self, sample: List = None):

        # Sample Classification
        if "classification" in sample:
            sample_classification = sample["classification"]
        else:
            sample_classification = 0

        menu = QMenu(self)
        menu.setTitle("Classification")
        for i in self.model.classifications:

            if sample_classification == i["number"]:
                icon = 0xF0133
                # menu.setIcon(FIcon(icon, item["color"]))
            else:
                icon = 0xF012F

            action = menu.addAction(FIcon(icon, i["color"]), i["name"])
            action.setData(i["number"])
            on_click = functools.partial(self.update_classification, i["number"])
            action.triggered.connect(on_click)

        return menu

    def _create_tags_menu(self):
        # Create classication action
        tags_menu = QMenu(self.tr("Tags"))

        tags_preset = Config("tags")

        for item in tags_preset.get("samples", []):

            icon = 0xF04F9

            action = tags_menu.addAction(FIcon(icon, item["color"]), item["name"])
            action.setData(item["name"])
            on_click = functools.partial(self.update_tags, [item["name"]])
            action.triggered.connect(on_click)

        return tags_menu

    def _setup_actions(self):

        # self.action_prev = self.tool_bar.addAction(FIcon(0xF0141), "Prev")
        # self.action_next = self.tool_bar.addAction(FIcon(0xF0142), "Next")

        self.add_action = self.tool_bar.addAction(
            FIcon(0xF0010), "Add Sample(s)", self.on_add_samples
        )
        self.rem_action = self.tool_bar.addAction(
            FIcon(0xF0BE5), "Remove selection", self.on_remove
        )

        self.clear_action = self.tool_bar.addAction(
            FIcon(0xF120A), "Clear sample(s)", self.on_clear_samples
        )

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.tool_bar.addWidget(spacer)

        # All samples button, create sources "samples"
        source_action = self.tool_bar.addAction(
            FIcon(0xF0A75), "Create source", self.on_create_samples_source
        )

        self.tool_bar.widgetForAction(source_action).setToolButtonStyle(Qt.ToolButtonTextBesideIcon)

        source_action.setToolTip(self.tr("Create subset from all samples and use it"))

        # Add genotypes for all samples
        genotype_action = self.tool_bar.addAction(
            # FIcon(0xF0B38), "Show genotypes", self.on_add_genotypes
            FIcon(0xF0AA1),
            "Show genotypes",
            self.on_add_genotypes,
        )

        self.tool_bar.widgetForAction(genotype_action).setToolButtonStyle(
            Qt.ToolButtonTextBesideIcon
        )

        genotype_action.setToolTip(self.tr("Add genotypes as fields from all samples"))

        self.select_action = QAction(FIcon(0xF0349), "Select variants")
        self.select_action.triggered.connect(self.on_show_variant)

        self.create_filter_action = QAction(FIcon(0xF0EF1), "Create filters")
        self.create_filter_action.triggered.connect(self.on_create_filter)

        self.clear_filter_action = QAction(FIcon(0xF0234), "Clear all filters")
        self.clear_filter_action.triggered.connect(self.on_clear_filters)

        self.source_action = QAction(FIcon(0xF0A75), "Create a source")
        self.source_action.triggered.connect(self.on_create_samples_source)
        self.genotype_action = QAction(FIcon(0xF0B38), "Add genotypes from all samples")
        self.genotype_action.triggered.connect(self.on_add_genotypes)

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        """override"""
        sample = self.model.get_sample(self.view.currentIndex().row())
        sample_name = sample.get("name", "unknown")
        sample_id = sample.get("id", 0)

        menu = QMenu(self)

        #menu.addAction(FIcon(0xF064F), f"Edit Sample '{sample_name}'", self.on_edit)
        menu.addAction(FIcon(0xF064F), f"Edit Sample '{sample_name}'", self.on_double_clicked) 

        menu.addMenu(self._create_classification_menu(sample))
        if not self.is_locked(sample_id):
            menu.addMenu(self._create_tags_menu())
        menu.addSeparator()

        fields_menu = menu.addMenu("Add genotype fields ...")

        for field in sql.get_field_by_category(self.model.conn, "samples"):
            field_action = fields_menu.addAction(QIcon(), field["name"], self.on_add_field)
            field_action.setData(field)

        menu.addAction(self.select_action)
        menu.addAction(self.create_filter_action)
        menu.addAction(self.clear_filter_action)
        menu.addAction(self.source_action)

        menu.exec(event.globalPos())

    def is_locked(self, sample_id: int):
        """Prevents editing genotype if sample is classified as locked
        A sample is considered locked if its classification has the boolean "lock: true" set in the Config (yml) file.

        Args:
            sample_id (int): sql sample id

        Returns:
            locked (bool) : lock status of sample attached to current genotype
        """
        config_classif = Config("classifications").get("samples", None)
        sample = sql.get_sample(self.model.conn, sample_id)
        sample_classif = sample.get("classification", None)

        if config_classif == None or sample_classif == None:
            return False

        locked = False
        for config in config_classif:
            if config["number"] == sample_classif and "lock" in config:
                if config["lock"] == True:
                    locked = True
        return locked

    def on_double_clicked(self):
        """
        Action on default doubleClick
        """
        self.on_edit()

    def on_double_clicked_vertical_header(self):
        """
        Action on doubleClick on verticalHeader
        """
        self.on_edit()

    def on_edit(self):

        sample = self.model.get_sample(self.view.currentIndex().row())
        # print(sample)
        if sample:
            dialog = SampleDialog(self.model.conn, sample["id"])

            if dialog.exec():
                # TODO : update only if  necessary
                self.model.load()

    def on_add_field(self):
        """
        Trigger by menu field_action
        """

        action = self.sender()
        field = action.data()
        field_name = field["name"]

        indexes = self.view.selectionModel().selectedRows()
        if indexes:
            sample_name = indexes[0].siblingAtColumn(0).data()

            fields = copy.deepcopy(self.mainwindow.get_state_data("fields"))
            new_field = f"samples.{sample_name}.{field_name}"

            fields.append(new_field)
            print(fields)
            self.mainwindow.set_state_data("fields", fields)
            self.mainwindow.refresh_plugins(sender=self)

    def on_remove(self):

        rows = []
        for index in self.view.selectionModel().selectedRows():
            rows.append(index.row())

        self.model.remove_samples(rows)
        self.on_model_changed()
        self.remove_all_sample_fields()
        self.on_create_samples_source(source_name=SAMPLES_SELECTION_NAME)

    def on_clear_samples(self):
        self.model.clear()
        self.on_model_changed()
        self.remove_all_sample_fields()
        self.on_create_samples_source(source_name=SAMPLES_SELECTION_NAME)

    def update_classification(self, value: int = 0):

        unique_ids = set()
        for index in self.view.selectionModel().selectedRows():
            if not index.isValid():
                continue

            sample = self.model.get_sample(index.row())
            sample_id = sample["id"]

            if sample_id in unique_ids:
                continue

            unique_ids.add(sample_id)
            update_data = {"classification": int(value)}
            self.model.update_sample(index.row(), update_data)

            LOGGER.debug(sample)

    def update_tags(self, tags: list = []):
        """Update tags of the variant

        Args:
            tags(list): A list of tags

        """

        for index in self.view.selectionModel().selectedRows():

            # current variant
            row = index.row()
            sample = self.model.get_sample(row)
            sample_id = sample["id"]

            # current sample tags
            current_sample = sql.get_sample(self.model.conn, sample_id)
            current_tags_text = current_sample.get("tags", None)
            if current_tags_text:
                current_tags = current_tags_text.split(cst.HAS_OPERATOR)
            else:
                current_tags = []

            # append tags
            for tag in tags:
                current_tags.append(tag) if tag not in current_tags else current_tags

            # update tags
            self.model.update_sample(row, {"tags": cst.HAS_OPERATOR.join(current_tags)})

    def on_show_variant(self):

        # Get current sample name
        indexes = self.view.selectionModel().selectedRows()

        if indexes:
            sample_name = indexes[0].siblingAtColumn(0).data()

            # Add GT field
            # fields = self.mainwindow.get_state_data("fields")
            # fields = [f for f in fields if not f.startswith("samples")]
            # fields += [f"samples.{sample_name}.gt"]

            self.on_add_genotypes(samples=[sample_name], refresh=False)

            # Create/Update current_sample source
            self.on_create_samples_source(
                source_name=CURRENT_SAMPLE_SELECTION_NAME, samples=[sample_name]
            )

            # self.mainwindow.set_state_data("fields", fields)
            # self.mainwindow.set_state_data("source", "current_sample")

            # self.mainwindow.refresh_plugins(sender=self)

            # if "source_editor" in self.mainwindow.plugins:
            #     self.mainwindow.refresh_plugin("source_editor")

    def on_create_filter(self):

        indexes = self.view.selectionModel().selectedRows()

        if indexes:
            sample_name = indexes[0].siblingAtColumn(0).data()

            filters = copy.deepcopy(self.mainwindow.get_state_data("filters"))

            if not filters:
                filters = {"$and": []}

            root = list(filters.keys())[0]  # Get first logic "$or" or "$and"

            # Append new filters
            filters[root].append({f"samples.{sample_name}.gt": {"$gt": 0}})

            self.mainwindow.set_state_data("filters", filters)

            # if "source_editor" in self.mainwindow.plugins:
            #     self.mainwindow.refresh_plugin("source_editor")

            self.mainwindow.refresh_plugins(sender=self)

    def on_clear_filters(self):

        indexes = self.view.selectionModel().selectedRows()

        if indexes:
            sample_name = indexes[0].siblingAtColumn(0).data()

            filters = self.mainwindow.get_state_data("filters")
            filters = querybuilder.remove_field_in_filter(filters, f"samples.{sample_name}.gt")

            self.mainwindow.set_state_data("filters", filters)

            self.mainwindow.refresh_plugins(sender=self)

    def on_create_samples_source(
        self, source_name: str = SAMPLES_SELECTION_NAME, samples: list = None
    ):
        """Create source from a list of samples

        Args:
            source_name: name of the source (default "samples")
            samples: list of samples for source (default all samples in the model)
        """
        if not samples:
            samples = self.model.get_samples()

        if len(samples):
            sql.insert_selection_from_samples(
                self.model.conn, samples, name=source_name, force=False
            )
            self.mainwindow.set_state_data("source", source_name)
            self.mainwindow.refresh_plugins(sender=self)
            if "source_editor" in self.mainwindow.plugins:
                self.mainwindow.refresh_plugin("source_editor")
        else:
            self.mainwindow.set_state_data("source", DEFAULT_SELECTION_NAME)
            self.mainwindow.refresh_plugins(sender=self)
            if "source_editor" in self.mainwindow.plugins:
                self.mainwindow.refresh_plugin("source_editor")

    def on_add_genotypes(self, samples: list = None, refresh=True):
        """Add from a list of samples

        Args:
            samples: list of samples for source (default all samples in the model)
        """
        if not samples:
            samples = self.model.get_samples()

        if samples:
            fields = self.mainwindow.get_state_data("fields")
            fields = [f for f in fields if not f.startswith("samples")]
            for sample_name in samples:
                # Add GT field
                fields += [f"samples.{sample_name}.gt"]

            self.mainwindow.set_state_data("fields", fields)
            if refresh:
                self.mainwindow.refresh_plugins(sender=self)

    def remove_all_sample_fields(self, refresh=False):
        """remove all fields from samples
        Args:

        """
        fields = self.mainwindow.get_state_data("fields")
        fields = [f for f in fields if not f.startswith("samples")]
        self.mainwindow.set_state_data("fields", fields)
        if refresh:
            self.mainwindow.refresh_plugins(sender=self)

    def on_register(self, mainwindow: MainWindow):
        """This method is called when the plugin is registered from the mainwindow.

        This is called one time at the application startup.

        Args:
            mainwindow (MainWindow): cutevariant Mainwindow
        """
        self.mainwindow = mainwindow

    def on_open_project(self, conn: sqlite3.Connection):
        """This method is called when a project is opened

                Do your initialization here.
        You may want to store the conn variable to use it later.

        Args:
            conn (sqlite3.connection): A connection to the sqlite project
        """
        self.model.clear()
        self.model.conn = conn

        # Chargement des classification

        config = Config("classifications")
        self.model.classifications = config.get("samples", [])
        self.model.load()

    def on_refresh(self):
        """This method is called from mainwindow.refresh_plugins()

        You may want to overload this method to update the plugin state
        when query changed
        """

        samples = self.mainwindow.get_state_data("samples")
        self.model.set_samples(copy.deepcopy(samples))
        self.model.load()
        self.on_model_changed()

    def on_close_project(self):
        self.model.clear()

    def _create_filters(self, copy_existing_filters: bool = True) -> dict:
        """
        The function creates a dictionary of filters based on a list of filters and existing filters (or not)

        Args:
            copy_existing_filters (bool, optional)

        Returns:
            dict: A dictionary of filters
        """
        indexes = self.view.selectionModel().selectedRows()

        if copy_existing_filters:
            filters = copy.deepcopy(self.mainwindow.get_state_data("filters"))
        else:
            filters = {}

        if not filters:
            root = "$and"
            filters["$and"] = []

        else:
            root = list(filters.keys())[0]
            for i in filters[root]:
                if i == previous_samples_filters:
                    filters[root].remove(i)

        selected_samples = self.mainwindow.get_state_data("selected_samples") or []

        # for index in indexes:
        if selected_samples:
            samples_filters = {}
            samples_filters["$or"] = []
            for sample_name in selected_samples:
                if sample_name:
                    key = f"samples.{sample_name}.gt"
                    condition = {key: {"$gte": 1}}
                    samples_filters["$or"].append(condition)

            filters[root].append(samples_filters)

        return filters


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)

    conn = sql.get_sql_connection("/home/sacha/exome.db")

    w = SamplesWidget()
    w.on_open_project(conn)

    w.show()

    app.exec()
