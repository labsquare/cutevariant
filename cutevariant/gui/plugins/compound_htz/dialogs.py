import sqlite3

from PySide6.QtGui import Qt
from PySide6.QtWidgets import (
    QCheckBox, 
    QGroupBox, 
    QLabel, 
    QSizePolicy, 
    QHBoxLayout, 
    QVBoxLayout, 
    QMessageBox, 
    QApplication, 
    QPushButton,
)

from cutevariant.config import Config
from cutevariant.core import sql
from cutevariant.core.vql import parse_vql
from cutevariant.gui.plugin import PluginDialog
from cutevariant.gui import MainWindow
from cutevariant.gui.plugins import compound_htz

class CompoundHtzDialog(PluginDialog):
    """Model class for all tool menu plugins

    These plugins are based on DialogBox; this means that they can be opened
    from the tools menu.
    """

    ENABLE = True

    def __init__(self, conn: sqlite3.Connection, parent: MainWindow=None) -> None:
        """
        Keys:
            parent (QMainWindow): cutevariant Mainwindow
        """
        super().__init__(parent)

        self.conn = conn
        self._load_settings()

        group_box = QGroupBox()
        header = QLabel()
        header.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        header.setText(self._get_header_text())
        header_layout = QHBoxLayout()
        header_layout.addWidget(header)
        group_box.setLayout(header_layout)

        self.checkbox = QCheckBox(f"Add tag {self.compound_htz_tag} to all selected variants", self)

        self.button = QPushButton("Select compound htz variants")
        self.button.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        self.button.clicked.connect(self._on_click)
        button_box = QVBoxLayout()
        button_box.setAlignment(Qt.AlignCenter)
        button_box.addWidget(self.button)

        self.setWindowTitle("Compound htz filter")
        self.vlayout = QVBoxLayout()
        self.vlayout.addWidget(group_box)
        self.vlayout.addWidget(self.checkbox)
        self.vlayout.addLayout(button_box)
        self.setLayout(self.vlayout)

    def _load_settings(self) -> None:
        config = Config("compound_htz")
        self.gene_field = config.get("gene_field", "ann.gene")
        self.vql_filter = config.get("vql_filter", None)
        self.compound_htz_tag = config.get("tag", "#COMPOUND_HTZ")

    def _get_header_text(self) -> str:

        text = f"""<b>Compound heterozygosity</b> is defined in settings as variants with:
        <ul>
            <li> same content in field: {self.gene_field}</li>
            <li> VQL filter: {self.vql_filter}</li>
        </ul>
        """
        return text

    def _get_variant_ids(self) -> list[str]:
        """Identify compound heterozygous variants = multiple variants in one gene.

        Returns:
            list[str]: list of variant ids
        """
        #Convert VQL to json
        if self.vql_filter == None:
            json_filter = {}
        else:
            for cmd in parse_vql("SELECT id FROM variants WHERE " + self.vql_filter):
                json_filter = cmd["filters"]

        variants = sql.get_variants(self.conn, ["id", self.gene_field], self.mainwindow.get_state_data("source"), json_filter, limit=None)
        ids_by_gene = {} # {gene1: [id1, id2], gene2: [id3]}
        for v in variants:
            if v[self.gene_field] in ids_by_gene:
                ids_by_gene[v[self.gene_field]].append(v["id"])
            else:
                ids_by_gene[v[self.gene_field]] = [v["id"]]

        id_list = []
        for gene in ids_by_gene:
            if len(ids_by_gene[gene]) > 1:
                id_list += ids_by_gene[gene]
        return id_list

    def _on_click(self) -> None:
        variants = self._get_variant_ids()

        if len(variants) != 0:
            filters = {"$and": [{"id": {"$in": variants}}]}

            if self.checkbox.checkState():
                #TODO: apply self.compound_htz_tag to all selected variants
                print("checked")

            self.mainwindow.set_state_data("filters", filters) #TODO: filters plugin can't handle so many ids. Find another way?
            self.mainwindow.refresh_plugins()

        else:
            QMessageBox.information(
                self, "No compound htz found", "Variant selection was unchanged"
            )

        self.close()

if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    conn = sql.get_sql_connection(
        "L:/Archives/NGS/BIO_INFO/BIO_INFO_Sam/scripts/cutevariant_project/devel_june2022.db"
    )
    dialog = CompoundHtzDialog(conn)
    dialog.exec()
