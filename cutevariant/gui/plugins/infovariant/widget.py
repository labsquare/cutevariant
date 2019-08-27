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
from cutevariant.gui.settings import SettingsWidget
from cutevariant.gui.ficon import FIcon
from cutevariant.gui.style import TYPE_COLORS
from cutevariant.commons import logger, WEBSITES_URLS

from cutevariant.core import sql, get_sql_connexion


LOGGER = logger()


class VariantPopupMenu(QMenu):
    """Class to display a contextual menu about the variant which is above the mouse

    .. note:: popup() is overrided and takes the variant as argument.
    """

    def __init__(self):
        super().__init__()

        self._variant = None

        # Fill menu
        self.addAction(FIcon(0xF4CE), self.tr("Add to Favorite")).setCheckable(True)
        self.addAction(
            FIcon(0xF18F), self.tr("Copy genomic location"), self.to_clipboard
        )

        # Create submenu for websites shortcuts
        self.sub_menu = self.addMenu(self.tr("Open With"))

    def sub_menu_setup(self):
        """Setup sub menu 'open with'
        .. note:: This function is called each time a context menu is requested
            in the aim of viewing new added databases into settings.
        """

        def add_action(site, url_template):
            """Build action, and connect it to a dynamically generated slot"""
            # This is not ok, Why ?
            # self.__dict__[f"open_{site}_url"] = Slot()(partial(self.open_url, url_template))

            # self.addAction(
            #     self.tr(f"Search the variant on {site}"), self, SLOT(f"open_{site}_url()")
            # )

            # Method to set the slot as a instance method
            # (if we want to use it elsewhere)
            # self.__dict__[f"open_{site}_url"] = partial(self.open_url, url_template)

            self.sub_menu.addAction(self.tr(site), partial(self.open_url, url_template))

        self.sub_menu.clear()

        # Built-in urls
        [add_action(*item) for item in WEBSITES_URLS.items()]

        # User urls - Get all child keys of the group databases_urls
        settings = QSettings()
        settings.beginGroup("databases_urls/")
        # Build menu actions
        [add_action(site, settings.value(site)) for site in settings.childKeys()]
        settings.endGroup()

        self.sub_menu.addSeparator()
        self.sub_menu.addAction(self.tr("Edit ..."), self.show_settings)

    def open_url(self, url_template):
        """Open the url based on the current variant and the given url template

        .. note:: URL ex: https://varsome.com/variant/hg19/chr17-7578406-C-A
        """

        url = url_template.format(**self._variant)

        LOGGER.info("InfoVariantWidget:open_url:: Open <%s>" % url)
        QDesktopServices.openUrl(QUrl(url))

    def to_clipboard(self):
        """Copy the current variant reference to the clipboard"""
        QApplication.clipboard().setText(
            "{chr}-{pos}-{ref}-{alt}".format(**self._variant)
        )

    def popup(self, variant: str, pos):
        """Overrided: Show the popup menu

        :param variant: Dictionnary that defines a variant (chr, pos, ref, alt).
        """
        self.sub_menu_setup()
        self._variant = variant
        super().popup(pos)

    def show_settings(self):
        """Slot to show settings window opened on the Variants page"""
        widget = SettingsWidget()
        # Open Settings on the Variants widget
        # We can also iterate over stacked widgets to find the good class name
        # w = widget.stack_widget.widget(2)
        # print(w.__class__.__name__)
        # widget.list_widget.setCurrentRow(2)
        w = widget.list_widget.findItems("Variants", Qt.MatchContains)[0]
        widget.list_widget.setCurrentItem(w)
        widget.exec()


class InfoVariantWidget(QWidget):
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