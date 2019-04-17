# Qt imports
from PySide2.QtCore import *
from PySide2.QtWidgets import *
from PySide2.QtGui import *

# Custom imports
from .plugin import VariantPluginWidget
from cutevariant.gui.ficon import FIcon
from cutevariant.gui.style import TYPE_COLORS
from cutevariant.commons import logger

LOGGER = logger()


class InfoVariantWidget(VariantPluginWidget):

    def __init__(self):
        super().__init__()

        self.setWindowTitle(self.tr("Info variants"))

        self.view = QTreeWidget()
        self.view.setColumnCount(2)
        self.view.setHeaderLabels([self.tr("Attributes"), self.tr("Values")])
        self._variant_ref = ""

        v_layout = QVBoxLayout()
        v_layout.setContentsMargins(0, 0, 0, 0)
        v_layout.addWidget(self.view)
        self.setLayout(v_layout)

    def menu_setup(self):
        """Setup popup menu

        .. todo:: Common menu with main variant window?
        """
        self.view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.menu = QMenu(self)
        self.menu.addAction(
            self.tr("Search the variant on Varsome"), self, SLOT("search_on_varsome()")
        )

        self.view.customContextMenuRequested.connect(self.show_menu)

    def populate(self, variant: dict):
        """Show the current variant attributes on the TreeWidget"""
        # Reset
        self.view.clear()

        # Filter None values
        g = ((key, val) for key, val in variant.items() if val)

        for key, val in g:
            item = QTreeWidgetItem()
            item.setText(0, str(key))
            item.setText(1, str(val))
            # item.setFlags(Qt.ItemIsSelectable|Qt.ItemIsEnabled)
            # map value type to color
            item.setIcon(
                0, FIcon(0xF70A, TYPE_COLORS[val.__class__.__name__])
            )

            self.view.addTopLevelItem(item)

    def set_variant(self, variant: dict):
        """Register and show the given variant"""
        self.populate(variant)
        self.build_variant_ref(variant)
        # The menu is available only when almost 1 variant is displayed
        self.menu_setup()

    def build_variant_ref(self, variant: dict):
        """Build variant standard reference"""

        self._variant_ref = f"%s-%s-%s-%s" % (
            variant["chr"],
            variant["pos"],
            variant["ref"],
            variant["alt"],
        )

    @Slot()
    def search_on_varsome(self):
        """Search the current variant on Varsome

        .. note:: URL ex: https://varsome.com/variant/hg19/chr17-7578406-C-A
        """
        LOGGER.info(
            "InfoVariantWidget:search_on_varsome:: Open <https://varsome.com/variant/hg19/%s>"
            % self._variant_ref
        )
        QDesktopServices.openUrl(
            QUrl("https://varsome.com/variant/hg19/" + self._variant_ref)
        )

    def show_menu(self, pos: QPoint):
        """Show menu"""
        self.menu.popup(self.view.mapToGlobal(pos))
