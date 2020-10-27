# Standard imports
import sqlite3

# Qt imports
from PySide2.QtWidgets import (
    QVBoxLayout,
    QTableView,
    QDialogButtonBox,
    QAbstractItemView,
    QHeaderView,
)
from PySide2.QtCore import Qt, QAbstractTableModel, QModelIndex, QThreadPool

# Custom imports
from cutevariant.gui.plugin import PluginDialog
from cutevariant.gui.sql_runnable import SqlRunnable
from cutevariant.core import sql


# SQL functions
def get_variant_count(conn: sqlite3.Connection):
    return conn.execute(
        "SELECT `count` FROM selections WHERE name = 'variants'"
    ).fetchone()["count"]


def get_variant_transition(conn: sqlite3.Connection):
    return conn.execute(
        """SELECT COUNT(*) AS `count` FROM variants
        WHERE (ref == 'A' AND alt == 'G')
        OR (ref == 'G' AND alt == 'A')
        OR (ref == 'C' AND alt == 'T')
        OR (ref == 'T' AND alt == 'C')"""
    ).fetchone()["count"]


def get_variant_transversion(conn: sqlite3.Connection):
    return conn.execute(
        """SELECT COUNT(*) AS `count` FROM variants
        WHERE (ref == 'A' AND alt == 'C')
        OR (ref == 'C' AND alt == 'A')
        OR (ref == 'G' AND alt == 'T')
        OR (ref == 'T' AND alt == 'G')
        OR (ref == 'G' AND alt == 'C')
        OR (ref == 'C' AND alt == 'G')
        OR (ref == 'A' AND alt == 'T')
        OR (ref == 'T' AND alt == 'A')"""
    ).fetchone()["count"]


def get_sample_count(conn: sqlite3.Connection):
    return conn.execute("SELECT COUNT(*) AS `count` FROM samples").fetchone()["count"]


def get_snp_count(conn: sqlite3.Connection):
    """Get the number of variants that are SNP

    Notes:
        This query is currently not covered by an index.
    """
    return conn.execute(
        "SELECT COUNT(*) AS `count` FROM variants WHERE is_snp = 1"
    ).fetchone()["count"]


class MetricModel(QAbstractTableModel):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.items = []

    def columnCount(self, parent=QModelIndex()) -> int:
        """ override """
        if parent == QModelIndex():
            return 2

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self.items)

    def data(self, index, role):

        if role == Qt.DisplayRole:
            return self.items[index.row()][index.column()]

    def clear(self):
        self.beginResetModel()
        self.items.clear()
        self.endResetModel()

    def add_metrics(self, name, value):

        self.beginInsertRows(QModelIndex(), len(self.items), len(self.items))
        self.items.append((name, value))
        self.endInsertRows()


class MetricsDialog(PluginDialog):

    ENABLE = True

    def __init__(self, conn=None, parent=None):
        super().__init__(parent)
        self.conn = conn

        self.view = QTableView()
        self.model = MetricModel()
        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok)

        self.view.setModel(self.model)
        self.view.setAlternatingRowColors(True)
        self.view.horizontalHeader().hide()
        self.view.verticalHeader().hide()
        self.view.setSelectionMode(QAbstractItemView.SingleSelection)
        self.view.setSelectionBehavior(QAbstractItemView.SelectRows)

        self.buttons.accepted.connect(self.accept)

        self.setWindowTitle(self.tr("Project metrics"))

        v_layout = QVBoxLayout()
        v_layout.addWidget(self.view)
        v_layout.addWidget(self.buttons)
        self.setLayout(v_layout)

        # Async stuff
        self.metrics_runnable = None
        self.populate()

    def populate(self):
        """Async implementation to populate the view

        Notes:
            When closing the dialog window, the thread is not stopped.
        """
        def compute_metrics(conn):
            """Async function"""
            return {
                "variants": get_variant_count(conn),
                "snps": get_snp_count(conn),
                "transitions": get_variant_transition(conn),
                "transversions": get_variant_transversion(conn),
                "samples": get_sample_count(conn),
            }

        self.model.add_metrics(self.tr("Loading..."), self.tr("data..."))

        self.metrics_runnable = SqlRunnable(self.conn, compute_metrics)
        self.metrics_runnable.finished.connect(self.loaded)
        QThreadPool.globalInstance().start(self.metrics_runnable)

    def loaded(self):
        """Called at the end of the thread and populate data"""
        results = self.metrics_runnable.results

        self.model.clear()
        ratio = results["transitions"] / results["transversions"]

        self.model.add_metrics("Variant count", results["variants"])
        self.model.add_metrics("Snp count", results["snps"])
        self.model.add_metrics("Transition count", results["transitions"])
        self.model.add_metrics("Transversion count", results["transversions"])
        self.model.add_metrics("Tr/tv ratio", ratio)
        self.model.add_metrics("Sample count", results["variants"])

        self.view.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeToContents
        )
        self.view.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)


if __name__ == "__main__":
    from PySide2.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)
    conn = sql.get_sql_connection("test.db")
    dialog = MetricsDialog(conn=conn)
    app.exec_()
