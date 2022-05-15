import sqlite3
from cutevariant.config import Config
from cutevariant.gui import plugin, style
from cutevariant.gui import MainWindow

from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtWidgets import *

from cutevariant.core import sql

from cutevariant.gui import FIcon
from cutevariant.gui.widgets import ChoiceWidget, create_widget_action, SampleDialog, SamplesDialog

# from gui.style import SAMPLE_CLASSIFICATION

SAMPLE_STYLE = {
    -1: {"name": "Rejected", "icon": 0xF012F, "color": "#ED6D79"},
    0: {"name": "Pending", "icon": 0xF012F, "color": "#F5A26F"},
    1: {"name": "Valided", "icon": 0xF012F, "color": "#71E096"},
}


class SampleModel(QAbstractTableModel):

    NAME_COLUMN = 0
    PHENOTYPE_COLUMN = 1
    SEX_COLUMN = 2
    COMMENT_COLUMN = 3

    def __init__(self, conn: sqlite3.Connection = None) -> None:
        super().__init__()
        self._samples = []
        self._selected_samples = []
        self.conn = conn

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
            color_alpha = QColor(color)
            color_alpha.setAlpha(100)
            if col == SampleModel.SEX_COLUMN:
                sex = sample.get("sex", None)
                if sex == 1:
                    return QIcon(FIcon(0xF029D))
                if sex == 2:
                    return QIcon(FIcon(0xF029C))
                if sex == 0:
                    return QIcon(FIcon(0xF029C, color_alpha))
            if col == SampleModel.PHENOTYPE_COLUMN:
                phenotype = sample.get("phenotype")
                if phenotype == 2:
                    return QIcon(FIcon(0xF0E95))
            if col == SampleModel.COMMENT_COLUMN:
                if sample["comment"]:
                    return QIcon(FIcon(0xF017A, color))
                else:
                    return QIcon(FIcon(0xF017A, color_alpha))

        if role == Qt.ToolTipRole:
            sample = self._samples[index.row()]
            if col == SampleModel.PHENOTYPE_COLUMN:
                if sample["phenotype"] == 2:
                    return "Affected"
            if col == SampleModel.SEX_COLUMN:
                sex = sample["sex"]
                if sex == 1:
                    return "Male"
                if sex == 2:
                    return "Female"

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

    def columnCount(self, index: QModelIndex = QModelIndex()):
        if index == QModelIndex():
            return 4
        else:
            return 0


class SampleVerticalHeader(QHeaderView):
    def __init__(self, parent=None):
        super().__init__(Qt.Vertical, parent)

    def sizeHint(self):
        return QSize(30, super().sizeHint().height())

    def paintSection(self, painter: QPainter, rect: QRect, section: int):

        if painter is None:
            return

        painter.save()
        super().paintSection(painter, rect, section)

        valid = self.model().get_sample(section).get("valid", -1)

        painter.restore()

        style = SAMPLE_STYLE.get(valid)
        color = style.get("color", "white")
        icon = style.get("icon", 0xF0EC8)

        pen = QPen(QColor(color))
        pen.setWidth(6)
        painter.setPen(pen)
        painter.setBrush(QBrush(color))
        painter.drawLine(rect.left(), rect.top() + 1, rect.left(), rect.bottom() - 1)

        target = QRect(0, 0, 16, 16)
        pix = FIcon(icon, color).pixmap(target.size())
        target.moveCenter(rect.center() + QPoint(1, 1))

        painter.drawPixmap(target, pix)


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

        self.view.setContextMenuPolicy(Qt.ActionsContextMenu)
        self.view.horizontalHeader().hide()
        self.view.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.view.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.view.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.view.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.view.doubleClicked.connect(self.on_run)

        self.view.setShowGrid(False)
        self.view.setSelectionMode(QAbstractItemView.SingleSelection)
        self.view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.view.setVerticalHeader(SampleVerticalHeader())
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

    def _setup_actions(self):

        # self.action_prev = self.tool_bar.addAction(FIcon(0xF0141), "Prev")
        # self.action_next = self.tool_bar.addAction(FIcon(0xF0142), "Next")

        self.add_action = self.tool_bar.addAction(FIcon(0xF0415), "Add Sample(s)", self.on_add_samples)
        self.clear_action = self.tool_bar.addAction(FIcon(0xF0413), "Clear sample(s)", self.on_clear_samples)
        self.edit_action = self.tool_bar.addAction(FIcon(0xF0FFB), "Edit  sample", self.on_edit)

        self.run_action = QAction(FIcon(0xF0FFB), "Show variant from selected sample")
        self.run_action.triggered.connect(self.on_run)
        self.source_action = QAction(FIcon(0xF0FFB), "Create source from selected sample")
        self.source_action.triggered.connect(self.on_create_source)

        self.view.addAction(self.edit_action)
        self.view.addAction(self.run_action)
        self.view.addAction(self.source_action)

    def on_edit(self):

        sample = self.model.get_sample(self.view.currentIndex().row())
        print(sample)
        if sample:
            dialog = SampleDialog(self.model.conn, sample["id"])

            if dialog.exec():
                # TODO : update only if  necessary
                self.model.load()

    def on_clear_samples(self):
        self.model.clear()

    def on_run(self):

        fields = self.mainwindow.get_state_data("fields")
        fields = [f for f in fields if not f.startswith("samples")]

        # hugly : Create genotype fields
        indexes = self.view.selectionModel().selectedRows()
        if indexes:
            sample_name = indexes[0].siblingAtColumn(0).data()

            fields += [f"samples.{sample_name}.gt"]

        self.mainwindow.set_state_data("fields", fields)
        self.mainwindow.set_state_data("filters", self._create_filters())
        self.mainwindow.refresh_plugins(sender=self)

    def on_create_source(self):
        name, success = QInputDialog.getText(self, self.tr("Source Name"), self.tr("Get a source name "))

        # if not name:
        #     return

        if success and name:

            sql.insert_selection_from_source(self.model.conn, name, "variants", self._create_filters(False))

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

        if not filters:
            root = "$or"
            filters["$or"] = []

        else:
            root = list(filters.keys())[0]
            filters[root] = [i for i in filters[root] if not list(i.keys())[0].startswith("samples")]

        for index in indexes:
            # sample_name = index.siblingAtColumn(1).data()
            sample_name = index.siblingAtColumn(0).data()
            if sample_name:
                key = f"samples.{sample_name}.gt"
                condition = {key: {"$gte": 1}}
                filters[root].append(condition)

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
