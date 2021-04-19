import sqlite3

from PySide2.QtGui import *
from PySide2.QtWidgets import *
from PySide2.QtCore import *

from cutevariant.core.sql import get_sql_connection, get_field_info, get_fields

from cutevariant.commons import logger

LOGGER = logger()


class StatsModel(QAbstractTableModel):
    metrics = {
        "mean": "The mean value of this field",
        "std": "Standard deviation",
        "min": "Lowest value of this field",
        "max": "Highest value of this field",
        "count": "Number of annotations for this field",
        "q1": "First quartile",
        "median": "Median",
        "q3": "Third quartile",
    }

    def __init__(self):
        super().__init__()

        self.cache = {}
        self.conn = None
        self.field = ""
        self.current_table = []

    def columnCount(self, index):
        return 2

    def rowCount(self, index):
        return len(self.current_table)

    def load(self, conn: sqlite3.Connection, field_name):

        if conn:
            self.conn = conn

            try:
                if field_name not in self.cache:
                    self.cache[field_name] = get_field_info(
                        self.conn, field_name, StatsModel.metrics.keys()
                    )
            except sqlite3.Error as e:
                LOGGER.error(e)
                return False
            except ArithmeticError as e:
                LOGGER.error(e)
                return False
            except Exception as e:
                LOGGER.error(e)
                return False

            self.beginResetModel()

            # If not cached, compute it

            # Current table is a list of tuples, based on key-value pairs stored in cache as a dictionnary
            self.current_table = list(self.cache[field_name].items())

            self.endResetModel()

            return True

    def data(self, index: QModelIndex, role):

        if not self.current_table:
            return

        if role == Qt.DisplayRole:

            return str(self.current_table[index.row()][index.column()])

        if role == Qt.ToolTipRole:
            metric_name = self.current_table[index.row()][0]
            return StatsModel.metrics.get(
                metric_name,
                self.tr(
                    "Oooops, something's wrong, I have no description for this one..."
                ),
            )

    def headerData(self, section, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return ["Field name", "Field value"][section]


class StatsWidget(QWidget):
    """
    Widget to show basic stats about a column in the cutevariant database
    """

    ENABLE = True

    def __init__(self, conn=None):
        super().__init__()
        self.conn = conn
        self.combobox_field = QComboBox(self)
        self.tableview_stats = QTableView(self)

        layout = QVBoxLayout(self)
        layout.addWidget(self.combobox_field)
        layout.addWidget(self.tableview_stats)

        self.stats_model = StatsModel()
        self.tableview_stats.setModel(self.stats_model)

        self.combobox_field.currentTextChanged.connect(
            self.on_current_field_selected_changed
        )
        self.last_field_selected = ""

    def on_current_field_selected_changed(self, new_text):
        if self.conn:
            if self.stats_model.load(self.conn, new_text):
                self.last_field_selected = new_text
            else:
                if self.last_field_selected:
                    self.combobox_field.blockSignals(True)
                    self.combobox_field.setCurrentText(self.last_field_selected)
                    self.combobox_field.blockSignals(False)

    def set_connection(self, conn: sqlite3.Connection):
        self.conn = conn
        self.combobox_field.clear()
        self.combobox_field.addItems(
            [
                field["name"]
                for field in get_fields(self.conn)
                if field["type"] in ("float", "int")
            ]
        )


class TestWidget(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.file_menu = self.menuBar().addMenu(self.tr("File"))
        self.file_menu.addAction(self.tr("Open"), self.open_database)
        self.file_menu.addAction(
            self.tr("Open hard-coded file name"),
            lambda: self.stats_widget.set_connection(
                get_sql_connection("/home/charles/Projets cutevariant/CFTR.db")
            ),
        )

        self.stats_widget = StatsWidget()
        self.setCentralWidget(self.stats_widget)

    def open_database(self):
        db_path = QFileDialog.getOpenFileName(
            self,
            self.tr("Please choose a cutevariant database file"),
            QDir.homePath(),
            self.tr("Cutevariant projects (*.db)"),
        )[0]
        conn = None
        if db_path:
            conn = get_sql_connection(db_path)
        if conn:
            self.stats_widget.set_connection(conn)


if __name__ == "__main__":
    import sys
    from PySide2.QtWidgets import QApplication

    app = QApplication(sys.argv)

    w = TestWidget()
    w.show()

    app.exec_()