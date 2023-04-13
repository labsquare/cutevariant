#!/usr/bin/env python
from PySide6.QtCore import *
from PySide6.QtWidgets import *
from PySide6.QtGui import *

import os
from cutevariant.core import command, vql, sql
from cutevariant.core.sql import get_sql_connection

from openpyxl import Workbook


def export_genotypes(database_file_name: str, vql_query: str, output: str, overwrite: bool = False):

    if not overwrite and os.path.isfile(output):
        return -1
    if not output:
        return -1
    conn = get_sql_connection(database_file_name)

    selected_variants = list(command.select_cmd(conn, **vql.parse_one_vql(vql_query), limit=0))

    all_samples = sorted([s["name"] for s in sql.get_samples(conn)])

    with open(output, "w") as f:

        TAB = "\t"
        LF = "\n"

        f.write(f"chr{TAB}pos{TAB}gene{TAB}{TAB.join(all_samples)}{LF}")

        for variant in selected_variants:
            chrom = variant["chr"]
            pos = variant["pos"]
            genotypes = sql.get_genotypes(conn, variant["id"], ["gt"], all_samples)

            f.write(
                f"{chrom}{TAB}{pos}{TAB}{variant['ann.gene']}{TAB}{TAB.join(str(s['gt'] or -1) for s in sorted(genotypes,key=lambda s:s['name']))}{LF}"
            )

    return 0


class ScriptInterface(QDialog):

    VQL_REQUEST = 0
    GENE_LIST = 1
    LOCI_LIST = 2

    def __init__(
        self, database_filename: str, current_vql_query: str, parent: QWidget = None
    ) -> None:
        super().__init__(parent)

        self.setWindowTitle(self.tr("Export genotypes..."))

        self.main_layout = QVBoxLayout(self)

        self._current_query_type = ScriptInterface.VQL_REQUEST

        self.query_type_combo = QComboBox(self)
        self.query_type_combo.addItem(
            self.tr("For current selection"), userData=ScriptInterface.VQL_REQUEST
        )
        self.query_type_combo.addItem(self.tr("By gene list"), userData=ScriptInterface.GENE_LIST)
        self.query_type_combo.addItem(
            self.tr("By loci list (chromosome,position)"), userData=ScriptInterface.LOCI_LIST
        )
        self.query_type_combo.setCurrentIndex(0)
        self.query_type_combo.currentIndexChanged.connect(self.query_type_changed)

        self.query_textbox = QTextEdit(self)
        self.query_textbox.textChanged.connect(self._update_query)
        self.query_textbox.hide()

        self.button_box = QDialogButtonBox(QDialogButtonBox.Cancel | QDialogButtonBox.Save)
        self.button_box.accepted.connect(self.save)
        self.button_box.rejected.connect(self.reject)

        self.main_layout.addWidget(self.query_type_combo)
        self.main_layout.addWidget(self.query_textbox)
        self.main_layout.addWidget(self.button_box)
        self.main_layout.addStretch(1)

        # Keep track of the original user query (this one is constant)
        self.user_query = current_vql_query

        self.db_filename = database_filename

    def save(self):

        if self._current_query_type == ScriptInterface.VQL_REQUEST:
            query = self.user_query
            vql_command = vql.parse_one_vql(self.query)
            if vql_command["cmd"] == "select_cmd":
                export_filename, filetype = QFileDialog.getSaveFileName(
                    self, self.tr("Save genotypes to..."), QDir.homePath()
                )
            export_genotypes(self.db_filename, self.query, export_filename)
            QMessageBox.information(self, self.tr("Done!"), self.tr("File saved successfully"))

        if self._current_query_type == ScriptInterface.GENE_LIST:
            output_dir = QFileDialog.getExistingDirectory(self)

            genes = self.query_textbox.toPlainText().split("\n")
            for gene in genes:
                query = f"SELECT chr,pos,ann.gene FROM variants WHERE ann.gene = '{gene}'"
                res = export_genotypes(
                    self.db_filename, query, os.path.join(output_dir, f"{gene}.csv")
                )
                if res == -1:
                    QMessageBox.critical(
                        self, self.tr("Error!"), self.tr("Could not save file, aborting!")
                    )
                    return
            QMessageBox.information(self, self.tr("Success!"), self.tr("Files saved successfully!"))

        if self._current_query_type == ScriptInterface.LOCI_LIST:
            query = self.vql_from_loci_list()
            export_filename, _ = QFileDialog.getSaveFileName(
                self, self.tr("Save genotypes to..."), QDir.homePath(), filter="CSV file (*.csv)"
            )
            export_genotypes(self.db_filename, self.query, export_filename)
            QMessageBox.information(self, self.tr("Done!"), self.tr("File saved successfully"))

    def query_type_changed(self, index: int):
        self._current_query_type = self.query_type_combo.currentData()

        if self.query_type_combo.currentData() == ScriptInterface.VQL_REQUEST:
            self.query_textbox.hide()
        else:
            self.query_textbox.show()

    def _update_query(self):
        self._current_query_type = self.query_type_combo.currentData(Qt.UserRole)
        if self._current_query_type == ScriptInterface.VQL_REQUEST:
            self.query_textbox.hide()

    def vql_from_loci_list(self):
        loci_list = self.query_textbox.toPlainText().split("\n")
        if not loci_list:
            return ""
        loci_filter = ""
        for locus in loci_list:
            l = locus.split("")
            if len(l) != 2:
                QMessageBox.warning(
                    self,
                    self.tr("Invalid locus"),
                    self.tr("Locus {0} is invalid, skipping it!").format(locus),
                )
                continue
            chrom, pos = l
            loci_filter += f" OR (chr = '{chrom}' AND pos = {pos})"
        return f"SELECT chr,pos,ann.gene FROM variants WHERE {loci_filter}"


if __name__ == "__main__":

    import sys

    app = QApplication(sys.argv)

    view = ScriptInterface("/home/charles/Bioinfo/ENaC/merged/all.db", "")
    view.open()

    app.exec()
