"""Plugin to show all characteristics of a selected variant

InfoVariantWidget is showed on the GUI, it uses VariantPopupMenu to display a
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

class InfoVariantWidget(PluginWidget):
    """Plugin to show all annotations of a selected variant"""

    def __init__(self):
        super().__init__()

        self.setWindowTitle(self.tr("Info variants"))

        self.view = QTabWidget()
        # build variant tab 
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

    def on_variant_changed(self, variant):
        self.current_variant = variant


    @property
    def conn(self):
        """ Return sqlite connexion of cutevariant project """
        return self._conn 

    @conn.setter
    def conn(self, conn):
        """Set sqlite connexion of a cutevariant project

        This method is called Plugin.on_open_project
        
        Args:
            conn (sqlite3.connection)
        """
        self._conn = conn

    @property
    def current_variant(self):
        """Return variant data as a dictionnary 
        """
        return self._current_variant

    @current_variant.setter
    def current_variant(self, variant):
        """Set variant data 
        This method is called by Plugin.on_variant_clicked """
        self._current_variant = variant
        self.populate()

    def populate(self):
        """Show the current variant attributes on the TreeWidget"""
       
        if "id" not in self.current_variant:
            return 

        variant_id = self.current_variant["id"]

        # Populate Variants 
        self.variant_view.clear()
        for key, value in sql.get_one_variant(self.conn, variant_id).items():
            item = QTreeWidgetItem()
            item.setText(0,key)
            item.setText(1,str(value))
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
        


    def show_menu(self, pos: QPoint):
        """Show context menu associated to the current variant"""
        if not self._variant:
            return
        self.context_menu.popup(self._variant, self.view.mapToGlobal(pos))


if __name__ == "__main__":
    import sys 
    app = QApplication(sys.argv)

    conn = get_sql_connexion("/home/schutz/Dev/cutevariant/examples/test.db")


    w = InfoVariantWidget()
    w.conn = conn

    variant = sql.get_one_variant(conn, 1)

    w.current_variant = variant

    w.show()

    app.exec_() 