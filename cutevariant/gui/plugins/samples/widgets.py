from logging import Logger
import sqlite3
import functools

from cutevariant import LOGGER
from cutevariant.config import Config
from cutevariant.gui import plugin, style
from cutevariant.gui import MainWindow

from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtWidgets import *

from cutevariant.core import sql
from cutevariant import constants as cst

from cutevariant.gui import FIcon
from cutevariant.gui.widgets import (
    SampleDialog,
    SamplesDialog,
)

# from gui.style import SAMPLE_CLASSIFICATION


class SampleModel(QAbstractTableModel):

    NAME_COLUMN = 0
    PHENOTYPE_COLUMN = 1
    SEX_COLUMN = 2
    COMMENT_COLUMN = 3
    # INFO_COLUMN = 4

    def __init__(self, conn: sqlite3.Connection = None) -> None:
        super().__init__()
        self._samples = []
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
        if orientation == Qt.Vertical and role == Qt.DecorationRole:
            return QColor("red")

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):

        col = index.column()

        if role == Qt.DisplayRole and col == SampleModel.NAME_COLUMN:
            sample = self._samples[index.row()]
            return sample.get("name")

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
                    return QIcon(FIcon(0xF08C9, color))
                if phenotype == 1:
                    return QIcon(FIcon(0xF05DD, color))
                else:
                    return QIcon(FIcon(0xF001A, color_alpha))

            if col == SampleModel.COMMENT_COLUMN:
                if sample["comment"]:
                    return QIcon(FIcon(0xF017A, color))
                else:
                    return QIcon(FIcon(0xF017A, color_alpha))
                # return QIcon(FIcon(0xF02FD, color))

        if role == Qt.ToolTipRole:

            sample = self._samples[index.row()]

            if col == SampleModel.COMMENT_COLUMN:
                comment = sample["comment"].replace("\n", "<br>")
                if comment:
                    return comment

            if col == SampleModel.NAME_COLUMN:
                return self.get_tooltip(index.row())

            if col == SampleModel.PHENOTYPE_COLUMN:
                return cst.PHENOTYPE_DESC.get(int(sample["phenotype"]), "Unknown")

            if col == SampleModel.SEX_COLUMN:
                return cst.SEX_DESC.get(int(sample["sex"]), "Unknown")

    def get_tooltip(self, row: int) -> str:
        """Return all samples info as a formatted text"""
        info = ""
        sample = self._samples[row]
        if "name" in sample:
            if sample["name"]:
                name = sample["name"]
                info += f"Sample <b>{name}</b><hr>"
        info += f"<table>"
        for sample_field in sample:
            if sample_field not in ["id"]:
                if sample_field != "name":
                    sample_field_value = str(sample[sample_field]).replace("\n", "<br>")
                    if sample_field == "phenotype":
                        sample_field_value = cst.PHENOTYPE_DESC.get(
                            int(sample[sample_field]), "Unknown"
                        )
                    if sample_field == "sex":
                        sample_field_value = cst.SEX_DESC.get(int(sample[sample_field]), "Unknown")
                    if sample_field == "classification":
                        sample_field_value = ""
                        style = None
                        for i in self.classifications:
                            if i["number"] == sample[sample_field]:
                                style = i
                        if style:
                            if "name" in style:
                                sample_field_value += style["name"]
                                if "description" in style:
                                    sample_field_value += f" (" + style["description"].strip() + ")"
                    info += f"<tr><td>{sample_field}</td><td width='20'></td><td>{sample_field_value}</td></tr>"
        info += f"</table>"
        return info

    def get_sample(self, row: int):
        if row >= 0 and row < len(self._samples):
            return self._samples[row]

    def set_samples(self, samples: list):
        self._selected_samples = samples
        self.load()

    def get_samples(self) -> list:
        return self._selected_samples

    def rowCount(self, index: QModelIndex = QModelIndex()):
        if index == QModelIndex():
            return len(self._samples)
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
            print(len(self._samples), row, rows)
            del self._samples[row]

        self.endResetModel()

    def columnCount(self, index: QModelIndex = QModelIndex()):
        if index == QModelIndex():
            return 4
        else:
            return 0


class SampleVerticalHeader(QHeaderView):
    def __init__(self, parent=None):
        super().__init__(Qt.Vertical, parent)
        self.mainwindow = parent

    def sizeHint(self):
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
            icon = 0xF012F

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

    # Location of the plugin in the mainwindow
    # Can be : DOCK_LOCATION, CENTRAL_LOCATION, FOOTER_LOCATION
    LOCATION = plugin.DOCK_LOCATION
    # Make the plugin enable. Otherwise, it will be not loaded
    ENABLE = True

    # Refresh the plugin only if the following state variable changed.
    # Can be : fields, filters, source

    REFRESH_STATE_DATA = {"fields", "filters"}

    def __init__(self, parent=None):
        super().__init__(parent)

        self.tool_bar = QToolBar()
        self.tool_bar.setIconSize(QSize(16, 16))
        self.view = QTableView()
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
        self.view.setModel(self.model)
        self.setContentsMargins(0, 0, 0, 0)

        self._setup_actions()

        self.view.horizontalHeader().hide()
        self.view.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.view.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.view.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.view.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.view.doubleClicked.connect(self.on_edit)
        # self.view.clicked.connect(self.on_run)

        self.view.setShowGrid(False)
        self.view.setSelectionMode(QAbstractItemView.SingleSelection)
        self.view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.view.setVerticalHeader(SampleVerticalHeader(parent))
        self.model.modelReset.connect(self.on_model_reset)

        self.stack_layout = QStackedLayout()
        self.stack_layout.addWidget(self.empty_widget)
        self.stack_layout.addWidget(self.view)
        self.stack_layout.setCurrentIndex(1)

        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.tool_bar)
        main_layout.addLayout(self.stack_layout)
        main_layout.setSpacing(0)

    def on_model_reset(self):

        if self.model.rowCount() > 0:
            self.stack_layout.setCurrentIndex(1)
        else:
            self.stack_layout.setCurrentIndex(0)

        self.mainwindow.set_state_data("samples", copy.deepcopy(self.model.get_samples()))
        self.mainwindow.refresh_plugins(sender=self)

    def _create_classification_menu(self):

        menu = QMenu(self)
        menu.setTitle("Classification")
        for i in self.model.classifications:
            action = menu.addAction(FIcon(0xF012F, i["color"]), i["name"])
            action.setData(i["number"])
            on_click = functools.partial(self.update_classification, i["number"])
            action.triggered.connect(on_click)

        return menu

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
        self.edit_action = self.tool_bar.addAction(FIcon(0xF0FFB), "Edit sample", self.on_edit)

        self.select_action = QAction(FIcon(0xF0FFB), "Add selected sample to filter variant")
        self.select_action.triggered.connect(self.on_select)
        self.unselect_action = QAction(FIcon(0xF0FFB), "Remove selected sample to filter variant")
        self.unselect_action.triggered.connect(self.on_unselect)

        self.source_action = QAction(FIcon(0xF0FFB), "Create source from selected sample")
        self.source_action.triggered.connect(self.on_create_source)

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:

        menu = QMenu(self)

        menu.addAction(self.edit_action)
        menu.addAction(self.rem_action)

        menu.addMenu(self._create_classification_menu())
        menu.addSeparator()
        menu.addAction(self.select_action)
        menu.addAction(self.unselect_action)
        menu.addAction(self.source_action)

        menu.exec(event.globalPos())

    def on_edit(self):

        sample = self.model.get_sample(self.view.currentIndex().row())
        # print(sample)
        if sample:
            dialog = SampleDialog(self.model.conn, sample["id"])

            if dialog.exec():
                # TODO : update only if  necessary
                self.model.load()

    def on_remove(self):

        rows = []
        for index in self.view.selectionModel().selectedRows():
            rows.append(index.row())

        self.model.remove_samples(rows)

    def on_clear_samples(self):
        self.model.clear()

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

    def on_select(self):

        fields = self.mainwindow.get_state_data("fields")
        fields = [f for f in fields if not f.startswith("samples")]

        # hugly : Create genotype fields
        indexes = self.view.selectionModel().selectedRows()
        selected_samples = self.mainwindow.get_state_data("selected_samples") or []
        if indexes:
            sample_name = indexes[0].siblingAtColumn(0).data()
            if sample_name not in selected_samples:
                selected_samples.append(sample_name)
        for sample_name in selected_samples:
            fields += [f"samples.{sample_name}.gt"]

        self.mainwindow.set_state_data("selected_samples", selected_samples)
        self.mainwindow.set_state_data("fields", fields)
        self.mainwindow.set_state_data("filters", self._create_filters())
        self.mainwindow.refresh_plugins(sender=self)
        # self.mainwindow.refresh_plugins("samples")
        self.on_model_reset()
        # print("selected_samples:")
        # print(self.mainwindow.get_state_data("selected_samples"))

    def on_unselect(self):

        fields = self.mainwindow.get_state_data("fields")
        fields = [f for f in fields if not f.startswith("samples")]

        # hugly : Create genotype fields
        indexes = self.view.selectionModel().selectedRows()
        selected_samples = self.mainwindow.get_state_data("selected_samples") or []
        if indexes:
            sample_name = indexes[0].siblingAtColumn(0).data()
            if sample_name in selected_samples:
                selected_samples.remove(sample_name)
        for sample_name in selected_samples:
            fields += [f"samples.{sample_name}.gt"]

        self.mainwindow.set_state_data("selected_samples", selected_samples)
        self.mainwindow.set_state_data("fields", fields)
        self.mainwindow.set_state_data("filters", self._create_filters())
        self.mainwindow.refresh_plugins(sender=self)
        # print("selected_samples:")
        # print(self.mainwindow.get_state_data("selected_samples"))

    def on_create_source(self):
        name, success = QInputDialog.getText(
            self, self.tr("Source Name"), self.tr("Get a source name ")
        )

        # if not name:
        #     return

        if success and name:

            sql.insert_selection_from_source(
                self.model.conn, name, "variants", self._create_filters(False)
            )

            if "source_editor" in self.mainwindow.plugins:
                self.mainwindow.refresh_plugin("source_editor")

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
        pass

    def on_add_samples(self):

        dialog = SamplesDialog(self.model.conn)
        dialog.set_samples(self.model.get_samples())
        if dialog.exec():
            self.model.set_samples(dialog.get_samples())

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

        previous_samples_filters = self.mainwindow.get_state_data("samples_filters")

        if not filters:
            root = "$or"
            filters["$or"] = []

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

            self.mainwindow.set_state_data("samples_filters", samples_filters)
            filters[root].append(samples_filters)

        return filters


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)

    conn = sql.get_sql_connection("/home/sacha/Dev/cutevariant/examples/test.db")

    w = SamplesWidget()
    w.model.conn = conn
    w.model.load()

    w.show()

    app.exec()
