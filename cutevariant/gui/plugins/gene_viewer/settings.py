## ================= Settings widgets ===================
# Qt imports
from PySide6.QtCore import *
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import *

# Custom imports
from cutevariant.gui.plugin import PluginSettingsWidget
from cutevariant.gui.settings import AbstractSettingsWidget
from cutevariant.gui import FIcon
import cutevariant.constants as cst

from cutevariant.gui.widgets import FileEdit

import sqlite3
import os
import gzip

import glob

import typing


def zipped_text_to_sqlite(ref_filename: str, db_filename: str):
    """Converts a zipped text file (.txt.gz) with genomic annotation data into a sqlite3 database

    Args:
        ref_filename (str): File name of the zipped text file containing the genomic annotation data
        db_filename (str): Path to save the database to

    Raises:
        FileNotFoundError: If ref_filename is not a path to an existing file
    """

    # Create databases
    conn = sqlite3.connect(db_filename)

    if not os.path.isfile(ref_filename):
        raise FileNotFoundError("%s : No such file or directory !")

    conn.execute(
        """
        CREATE TABLE genes(  
        id INTEGER PRIMARY KEY,
        transcript_name TEXT, 
        tx_start INTEGER, 
        tx_end INTEGER,
        cds_start INTEGER,
        cds_end INTEGER,
        exon_starts TEXT,
        exon_ends TEXT,
        gene TEXT
        )

    """
    )

    data = []
    with gzip.open(ref_filename, "rb") as file:
        for index, line in enumerate(file):
            if line:
                line = line.decode("utf-8").strip().split("\t")

                transcript = line[1]
                txStart = line[4]
                txEnd = line[5]
                cdsStart = line[6]
                cdsEnd = line[7]
                exonStarts = ",".join([i for i in line[9].split(",") if i.isnumeric()])
                exonEnds = ",".join([i for i in line[10].split(",") if i.isnumeric()])
                gene = line[12]

                data.append(
                    (
                        None,
                        transcript,
                        txStart,
                        txEnd,
                        cdsStart,
                        cdsEnd,
                        exonStarts,
                        exonEnds,
                        gene,
                    )
                )

    conn.executemany("INSERT INTO genes VALUES(?,?,?,?,?,?,?,?,?);", data)
    conn.commit()


def open_link(url: typing.Union[QUrl, str]):
    if isinstance(url, QUrl):
        if url.toString() == "#annotation-reference-database-guidelines":
            dialog = GuidelinesDialog()
            dialog.exec_()
    elif isinstance(url, str):
        if url == "#annotation-reference-database-guidelines":
            dialog = GuidelinesDialog()
            dialog.exec_()

    def save(self):
        """Override from PageWidget"""
        pass

    def load(self):
        """Override from PageWidget"""

        # Load view that lists all available annotation reference databases
        # settings = self.create_settings()
        # self._database_folder_path = settings.value(
        #     "database_folder_path", QDir.homePath()
        # )
        # self.line_edit_database_folder_path.setText(self._database_folder_path)
        # self.db_model.load(self._database_folder_path)

        pass


class FieldSettings(AbstractSettingsWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Fields")
        label = QLabel(
            """
            Select Fields to use to select corresponding gene of the selected variants 
            """
        )
        label.setTextFormat(Qt.RichText)

        field_layout = QFormLayout(self)
        self.gene_edit = QLineEdit()
        self.gene_edit.setPlaceholderText("ann.gene")
        self.transcript_edit = QLineEdit()
        self.transcript_edit.setPlaceholderText("ann.transcript")
        field_layout.addRow("Gene field", self.gene_edit)
        field_layout.addRow("Transcript field", self.transcript_edit)

    def save(self):

        config = self.section_widget.create_config()
        config["gene_field"] = self.gene_edit.text()
        config["transcript_field"] = self.transcript_edit.text()
        config.save()

    def load(self):
        config = self.section_widget.create_config()
        gene = config.get("gene_field", "ann.gene")
        transcript = config.get("transcript_field", "ann.transcript")
        self.gene_edit.setText(gene)
        self.transcript_edit.setText(transcript)


class DataBaseSettings(AbstractSettingsWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gene Database")

        label = QLabel(
            """
            You can create a transcript database from an UCSC RefSeq textfile. <br/>
            Ex : For Human hg19, <a href='https://hgdownload.cse.ucsc.edu/goldenPath/hg19/database/refGene.txt.gz'> Download the file here   </a>
            """
        )

        label.setTextFormat(Qt.RichText)
        label.setOpenExternalLinks(True)

        # DB layout
        db_layout = QFormLayout()
        self.edit = FileEdit()
        self.button = QPushButton("Create database from Refseq")
        self.button.clicked.connect(self._on_create_db)
        db_layout.addRow("Database path", self.edit)
        db_layout.addRow("", self.button)

        v_layout = QVBoxLayout(self)
        v_layout.addWidget(label)
        v_layout.addLayout(db_layout)
        v_layout.addStretch()

    def _on_create_db(self):

        path, _ = QFileDialog.getOpenFileName(
            self, "txt.gz", QDir.homePath(), "RefSeq file (*.txt.gz)"
        )

        db_path = path.replace("txt.gz", "db")

        if os.path.exists(db_path):
            os.remove(db_path)

        try:
            zipped_text_to_sqlite(path, db_path)
        except Exception as e:
            QMessageBox.critical(self, "error", f"Cannot create database\n {e}")
            return

        self.edit.setText(db_path)

    def save(self):

        config = self.section_widget.create_config()
        config["db_path"] = self.edit.text()
        config.save()

    def load(self):
        config = self.section_widget.create_config()
        path = config.get("db_path", "")
        self.edit.setText(path)


class GeneViewerSettingsWidget(PluginSettingsWidget):
    """Instantiated plugin in the settings panel of Cutevariant

    Allows users to choose the annotation database used by the geneviewer.
    It is the responsibility of the user to have a database with gene name entries that match gene names from the VCF they are analyzing.
    """

    ENABLE = True

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowIcon(FIcon(0xF11CC))
        self.setWindowTitle("Gene viewer")
        self.add_page(DataBaseSettings())
        self.add_page(FieldSettings())


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    dlg = GeneViewerSettingsWidget()
    dlg.show()
    exit(app.exec_())
