"""Plugin to show all characteristics of a selected variant

VariantInfoWidget is showed on the GUI, it uses VariantPopupMenu to display a
contextual menu about the variant which is selected.
VariantPopupMenu is also used in viewquerywidget for the same purpose.
"""
# Standard imports
from functools import partial

# Qt imports
from PySide2.QtCore import Qt, QPoint, QSettings, QUrl, Slot
from PySide2.QtWidgets import *
from PySide2.QtGui import QDesktopServices

# Custom imports
from cutevariant.gui.ficon import FIcon
from cutevariant.gui.style import TYPE_COLORS
from cutevariant.core import sql, get_sql_connexion

from cutevariant.gui.plugin import PluginWidget

class VariantInfoWidget(PluginWidget):
    """Plugin to show all annotations of a selected variant"""

    ACMG_CLASSIFICATION = [
        ("Classe 0", "Unclassed"),
        ("Classe 1", "Benin"),
        ("Classe 2", "Likely benin"),
        ("Classe 3","Unsignificant variant"),
        ("Classe 4","Probably Pathogen"),
        ("Classe 5","Pathogen")
    ]


    ENABLE = True

    def __init__(self,conn = None):
        super().__init__()

        self.conn = conn

        self.setWindowTitle(self.tr("Info variants"))

        self.view = QTabWidget()
        # Editor 
        self.classification_box = QComboBox()
        self.favorite_checkbox = QCheckBox()
        self.comment_input = QTextEdit()
        self.save_button = QPushButton("Save")
        for a,b in self.ACMG_CLASSIFICATION:
            self.classification_box.addItem(a,b)

        self.editor = QWidget()
        self.editor_layout = QVBoxLayout()

        self.toolbar = QToolBar()
        self.toolbar.setIconSize(QSize(16,16))

        sub_edit_layout = QFormLayout()
        sub_edit_box = QGroupBox()
        #editor_layout.setRowWrapPolicy(QFormLayout.WrapAllRows)
        sub_edit_layout.addRow("Classification", self.classification_box)
        sub_edit_layout.addRow("Is Saved", self.favorite_checkbox)
        sub_edit_box.setLayout(sub_edit_layout)
        #sub_edit_layout.addWidget(self.comment_input)
        #sub_edit_layout.addWidget(self.save_button)

        self.editor_layout.addWidget(sub_edit_box)
        self.editor_layout.addWidget(self.comment_input)
        self.editor_layout.addWidget(self.save_button)


        self.editor.setLayout(self.editor_layout)
        self.view.addTab(self.editor, "User")
        self.save_button.clicked.connect(self.on_save_clicked)


        # Build variant tab 
        self.variant_view = QTreeWidget()
        self.variant_view.setColumnCount(2)
        self.variant_view.setHeaderLabels(["Field","Value"])
        self.view.addTab(self.variant_view, "Variants")
        


        # build transcript tab 
        self.transcript_combo = QComboBox()
        self.transcript_view = QTreeWidget()
        self.transcript_view.setColumnCount(2)
        self.transcript_view.setHeaderLabels(["Field","Value"])
        tx_layout = QVBoxLayout()
        tx_layout.addWidget(self.transcript_combo)
        tx_layout.addWidget(self.transcript_view)
        tx_widget = QWidget()
        tx_widget.setLayout(tx_layout)
        self.view.addTab(tx_widget,"Transcripts")
        self.transcript_combo.currentIndexChanged.connect(self.on_transcript_changed)

        # build Samples tab 
        self.sample_combo = QComboBox()
        self.sample_view = QTreeWidget()
        self.sample_view.setColumnCount(2)
        self.sample_view.setHeaderLabels(["Field","Value"])
        tx_layout = QVBoxLayout()
        tx_layout.addWidget(self.sample_combo)
        tx_layout.addWidget(self.sample_view)
        tx_widget = QWidget()
        tx_widget.setLayout(tx_layout)
        self.view.addTab(tx_widget,"Samples")
        self.sample_combo.currentIndexChanged.connect(self.on_sample_changed)


        # Build genotype tabs 
        self.genotype_view = QListWidget()
        self.genotype_view.setIconSize(QSize(20,20))
        self.view.addTab(self.genotype_view, "Genotypes")

    
       # self.view.setColumnCount(2)
        # Set title of columns
       # self.view.setHeaderLabels([self.tr("Attributes"), self.tr("Values")])

        v_layout = QVBoxLayout()
        v_layout.setContentsMargins(0, 0, 0, 0)
        v_layout.addWidget(self.view)
        self.setLayout(v_layout)

        # # Create menu
        # self.context_menu = VariantPopupMenu()
        # # Ability to trigger the menu
        # self.view.setContextMenuPolicy(Qt.CustomContextMenu)
        # self.view.customContextMenuRequested.connect(self.show_menu)

        # self._variant = dict()

        #self.add_tab("variants")


    def on_open_project(self, conn):
        self.conn = conn
        self.on_refresh()

    def on_refresh(self):
        self.current_variant = self.mainwindow.state.current_variant
        self.populate()

    def populate(self):
        """Show the current variant attributes on the TreeWidget"""
        if not self.current_variant:
            return 

        if "id" not in self.current_variant:
            return 

        variant_id = self.current_variant["id"]

        # Populate Variants 
        self.variant_view.clear()
        for key, value in sql.get_one_variant(self.conn, variant_id).items():
            item = QTreeWidgetItem()
            item.setText(0,key)
            item.setText(1,str(value))

            if key == "classification":
                self.classification_box.setCurrentIndex(int(value))

            if key == "comment":
                self.comment_input.setText(str(value))

            if key == "favorite":
                self.favorite_checkbox.setChecked(bool(value))

            self.variant_view.addTopLevelItem(item)

        # Populate annotations
        self.transcript_combo.blockSignals(True)
        self.transcript_combo.clear()
        for annotation in sql.get_annotations(self.conn, variant_id):
            if "transcript" in annotation:
                self.transcript_combo.addItem(annotation["transcript"], annotation)
        self.on_transcript_changed()
        self.transcript_combo.blockSignals(False)

        # Populate samples
        self.sample_combo.blockSignals(True)
        self.sample_combo.clear()
        for sample in sql.get_samples(self.conn):
            self.sample_combo.addItem(sample["name"], sample["id"])
        self.on_sample_changed()
        self.sample_combo.blockSignals(False)


        # Populate genotype 
        self.genotype_view.clear()
        q = f"SELECT samples.name, sv.gt FROM samples LEFT JOIN sample_has_variant sv ON samples.id = sv.sample_id AND sv.variant_id = {variant_id}"
        
        # TODO : move somewhere else
        GENOTYPES = {
        -1: FIcon(0xF2D7),
        0: FIcon(0xF130),
        1: FIcon(0xFAA0),
        2: FIcon(0xFAA4)}

        for row in self.conn.execute(q):
            item = QListWidgetItem() 
            genotype = int(row[1])
            icon = GENOTYPES[genotype]

            item.setText(str(row[0]))
            item.setIcon(icon)
            
            self.genotype_view.addItem(item)

        # cur = self.conn.cursor()
        # cur.execute(q)
       


        # for sample in sql.get_samples(self.conn):
        #     item = QTreeWidgetItem()
        #     item.setText(0, sample["name"])
        #     self.genotype_view.addTopLevelItem(item)


    @Slot()
    def on_transcript_changed(self):
        """This method is triggered when transcript change from combobox
        """
        annotations = self.transcript_combo.currentData()
        self.transcript_view.clear()
        if annotations:
            for key, val in annotations.items():
                item = QTreeWidgetItem()
                item.setText(0, key)
                item.setText(1, str(val))
                
                self.transcript_view.addTopLevelItem(item)

    @Slot()
    def on_sample_changed(self):
        """This method is triggered when sample change from combobox
        """
        sample_id = self.sample_combo.currentData()
        variant_id = self.current_variant["id"]
        self.sample_view.clear()
        ann = sql.get_sample_annotations(self.conn, variant_id, sample_id)
        if ann:
            for key, value in ann.items():
                item = QTreeWidgetItem()
                item.setText(0, key)
                item.setText(1, str(value))
                self.sample_view.addTopLevelItem(item)
        

    @Slot()
    def on_save_clicked(self):
        """Save button 
        """
        classification = self.classification_box.currentIndex() 
        favorite = self.favorite_checkbox.isChecked()
        comment = self.comment_input.toPlainText()

        updated = {
            "id": self.current_variant["id"],
            "classification": classification,
            "favorite": favorite,
            "comment": comment
            }

        sql.update_variant(self.conn, updated)

        

    def show_menu(self, pos: QPoint):
        """Show context menu associated to the current variant"""
        if not self._variant:
            return
        self.context_menu.popup(self._variant, self.view.mapToGlobal(pos))


if __name__ == "__main__":
    import sys 
    app = QApplication(sys.argv)

    conn = get_sql_connexion("/home/schutz/Dev/cutevariant/examples/test.db")


    w = VariantInfoWidget()
    w.conn = conn

    variant = sql.get_one_variant(conn, 1)

    w.current_variant = variant

    w.show()

    app.exec_() 