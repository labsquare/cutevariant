# Standard imports
import sqlite3

# Qt imports
from PySide2.QtWidgets import (
    QVBoxLayout,
    QTableView,
    QDialogButtonBox,
    QAbstractItemView,
    QHeaderView,
    QTabWidget,
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

def get_indel_count(conn: sqlite3.Connection):
    """Get the number of variants that are SNP

    Notes:
        This query is currently not covered by an index.
    """
    return conn.execute(
        "SELECT COUNT(*) AS `count` FROM variants WHERE is_indel = 1"
    ).fetchone()["count"]




def get_gene_counts(conn: sqlite3.Connection):
    """ Get the number of variant per genes """ 
    results = {}
    for record in conn.execute(
        "SELECT gene, COUNT(*) as 'count' FROM annotations GROUP BY gene ORDER by count DESC LIMIT 1,100"
    ):
        results[record["gene"]] = record["count"]

    return results





class KeyValueModel(QAbstractTableModel):
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


class KeyValueWidget(QTableView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.model = KeyValueModel()
        self.setModel(self.model)
        self.setAlternatingRowColors(True)
        self.horizontalHeader().hide()
        self.verticalHeader().hide()
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)

    def set_data(self, data: dict):
        self.model.clear()

        for key in data.keys():
            self.model.add_metrics(key, str(data[key]))

        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)

    def show_loading(self):
        self.model.clear()
        self.model.add_metrics("Loading ...", "Data ...")

class MetricsDialog(PluginDialog):

    ENABLE = True

    def __init__(self, conn=None, parent=None):
        super().__init__(parent)
        self.conn = conn

        self.tab_widget = QTabWidget()

        self.meta_view = KeyValueWidget()
        self.stat_view = KeyValueWidget()
        self.ann_view = KeyValueWidget()

        self.tab_widget.addTab(
            self.meta_view, "Metadata",
        )
        self.tab_widget.addTab(self.stat_view, "Variants")
        self.tab_widget.addTab(self.ann_view, "Annotations")

        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok)

        self.buttons.accepted.connect(self.accept)

        self.setWindowTitle(self.tr("Project metrics"))

        v_layout = QVBoxLayout()
        v_layout.addWidget(self.tab_widget)
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

            meta_data = sql.get_metadatas(conn)

            stats_data = {
                "Variant count": get_variant_count(conn),
                "Snp count": get_snp_count(conn),
                "Indel count": get_indel_count(conn),
                "Transition count": get_variant_transition(conn),
                "Transversion count": get_variant_transversion(conn),
                "Sample count": get_sample_count(conn),
            }

            stats_data["Tr/tv ratio"] = (
                round(stats_data["Transition count"] / stats_data["Transversion count"],2)
            )

            if sql.table_exists(conn, "annotations"):
                genes_data = get_gene_counts(conn)
            else:
                gene_data = {}

            return meta_data, stats_data, genes_data

        self.stat_view.show_loading()
        self.meta_view.show_loading()

        self.metrics_runnable = SqlRunnable(self.conn, compute_metrics)
        self.metrics_runnable.finished.connect(self.loaded)
        QThreadPool.globalInstance().start(self.metrics_runnable)

    def loaded(self):
        """Called at the end of the thread and populate data"""
        meta_data, stats_data, genes_data = self.metrics_runnable.results

        self.stat_view.set_data(stats_data)
        self.meta_view.set_data(meta_data)
        self.ann_view.set_data(genes_data)


if __name__ == "__main__":
    from PySide2.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)
    conn = sql.get_sql_connection("test.db")
    dialog = MetricsDialog(conn=conn)
    app.exec_()
