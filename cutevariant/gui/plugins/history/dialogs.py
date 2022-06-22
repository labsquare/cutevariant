# Standard imports
import sqlite3

# Qt imports
from PySide6.QtWidgets import (
    QVBoxLayout,
    QTableView,
    QDialogButtonBox,
    QAbstractItemView,
    QHeaderView,
    QTabWidget,
    QStatusBar,
)
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex, QThreadPool

# Custom imports
from cutevariant.gui.plugin import PluginDialog
from cutevariant.gui.sql_thread import SqlThread
from cutevariant.gui.widgets import DictWidget
from cutevariant.core import sql


# SQL functions
def get_variant_count(conn: sqlite3.Connection):
    return conn.execute("SELECT `count` FROM selections WHERE name = 'variants'").fetchone()[
        "count"
    ]


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
    return conn.execute("SELECT COUNT(*) AS `count` FROM variants WHERE is_snp = 1").fetchone()[
        "count"
    ]


def get_indel_count(conn: sqlite3.Connection):
    """Get the number of variants that are SNP

    Notes:
        This query is currently not covered by an index.
    """
    return conn.execute("SELECT COUNT(*) AS `count` FROM variants WHERE is_indel = 1").fetchone()[
        "count"
    ]


def get_gene_counts(conn: sqlite3.Connection):
    """Get the number of variant per genes"""
    results = {}
    for record in conn.execute(
        "SELECT gene, COUNT(*) as 'count' FROM annotations GROUP BY gene ORDER by count DESC LIMIT 1,100"
    ):
        results[record["gene"]] = record["count"]

    return results


def get_history_variants(conn: sqlite3.Connection):
    """Get the history of samples"""
    results = {}
    for record in conn.execute(
        f"""SELECT   ('[' || `timestamp` || ']') as gene,
                    ( '[' || `user` || ']' || ' - ' || '[' || `variants`.`chr` || '-' || `variants`.`pos` || '-' || `variants`.`ref` || '-' || `variants`.`alt` || ']' || ' - ' || '"' || `field` || '" from "' || `before` || '" to "' || `after` || '"') as 'count'
            FROM `history`
            INNER JOIN `variants` ON `history`.`table_rowid`=`variants`.`rowid`
            WHERE `table`='variants'"""
    ):
        results[record["gene"]] = record["count"]

    return results


def get_history_genotypes(conn: sqlite3.Connection):
    """Get the history of samples"""
    results = {}
    for record in conn.execute(
        f"""SELECT  ('[' || `timestamp` || ']') as gene,
                    ( '[' || `user` || ']' || ' - ' || '[' || `samples`.`name` || '|' || `variants`.`chr` || '-' || `variants`.`pos` || '-' || `variants`.`ref` || '-' || `variants`.`alt` || '] '  || ' - ' || '"' || `field` || '" from "' || `before` || '" to "' || `after` || '"') as 'count'
            FROM `history`
            INNER JOIN `genotypes` ON `history`.`table_rowid`=`genotypes`.`rowid`
            INNER JOIN `variants` ON `genotypes`.`variant_id`=`variants`.`id`
            INNER JOIN `samples` ON `genotypes`.`sample_id`=`samples`.`id` 
            WHERE `table`='genotypes'"""
    ):
        results[record["gene"]] = record["count"]

    return results


def get_history_samples(conn: sqlite3.Connection):
    """Get the history of samples"""
    results = {}
    for record in conn.execute(
        f"""SELECT  ('[' || `timestamp` || ']') as gene,
                    ( '[' || `user` || ']' || ' - ' || '[' || `samples`.`name` || ']' || ' - ' || '"' || `field` || '" from "' || `before` || '" to "' || `after` || '"') as 'count'
            FROM `history`
            INNER JOIN `samples` ON `history`.`table_rowid`=`samples`.`rowid`
            WHERE `table`='samples'"""
    ):
        results[record["gene"]] = record["count"]

    return results


class HistoryDialog(PluginDialog):

    ENABLE = True

    def __init__(self, conn=None, parent=None):
        super().__init__(parent)
        self.conn = conn

        self.tab_widget = QTabWidget()
        self.status_bar = QStatusBar()

        self.meta_view = DictWidget()
        self.stat_view = DictWidget()
        self.ann_view = DictWidget()

        self.tab_widget.addTab(self.meta_view, "Variants classification")
        self.tab_widget.addTab(self.stat_view, "Variants validation")
        self.tab_widget.addTab(self.ann_view, "Samples annotation")

        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok)

        self.buttons.accepted.connect(self.accept)

        self.setWindowTitle(self.tr("History"))

        v_layout = QVBoxLayout()
        v_layout.addWidget(self.tab_widget)
        v_layout.addWidget(self.status_bar)
        v_layout.addWidget(self.buttons)
        v_layout.setSpacing(0)
        self.setLayout(v_layout)

        self.resize(800, 600)
        # Async stuff
        self.metric_thread = None
        self.populate()

    def populate(self):
        """Async implementation to populate the view

        Notes:
            When closing the dialog window, the thread is not stopped.
        """

        def compute_metrics(conn):
            """Async function"""

            # meta_data = sql.get_metadatas(conn)

            # stats_data = {
            #     "Variant count": get_variant_count(conn),
            #     "Snp count": get_snp_count(conn),
            #     "Indel count": get_indel_count(conn),
            #     "Transition count": get_variant_transition(conn),
            #     "Transversion count": get_variant_transversion(conn),
            #     "Sample count": get_sample_count(conn),
            # }

            # stats_data["Tr/tv ratio"] = round(
            #     stats_data["Transition count"] / stats_data["Transversion count"], 2
            # )

            # if sql.table_exists(conn, "history"):
            #     genes_data = get_gene_counts(conn)
            # else:
            #     genes_data = {}

            # return meta_data, stats_data, genes_data

            if sql.table_exists(conn, "history"):
                meta_data = get_history_variants(conn)
                stats_data = get_history_genotypes(conn)
                genes_data = get_history_samples(conn)
            else:
                meta_data = {}
                stats_data = {}
                genes_data = {}

            return meta_data, stats_data, genes_data

        self.status_bar.showMessage("Loading ...")
        self.metric_thread = SqlThread(self.conn, compute_metrics)
        self.metric_thread.result_ready.connect(self.loaded)
        self.metric_thread.start()

    def loaded(self):
        """Called at the end of the thread and populate data"""
        meta_data, stats_data, genes_data = self.metric_thread.results

        self.stat_view.set_dict(stats_data)
        self.meta_view.set_dict(meta_data)
        self.ann_view.set_dict(genes_data)
        self.status_bar.showMessage("")


if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)
    conn = sql.get_sql_connection("test.db")
    dialog = HistoryDialog(conn=conn)
    app.exec_()
