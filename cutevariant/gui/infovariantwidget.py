# Standard imports
from functools import partial

# Qt imports
from PySide2.QtCore import *
from PySide2.QtWidgets import *
from PySide2.QtGui import *

# Custom imports
from .plugin import VariantPluginWidget
from cutevariant.gui.ficon import FIcon
from cutevariant.gui.style import TYPE_COLORS
from cutevariant.commons import logger, WEBSITES_URLS

LOGGER = logger()


class InfoVariantWidget(VariantPluginWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle(self.tr("Info variants"))

        self.view = QTreeWidget()
        self.view.setColumnCount(2)
        self.view.setHeaderLabels([self.tr("Attributes"), self.tr("Values")])
        self._variant = dict()

        v_layout = QVBoxLayout()
        v_layout.setContentsMargins(0, 0, 0, 0)
        v_layout.addWidget(self.view)
        self.setLayout(v_layout)

        self.menu_setup()

    def menu_setup(self):
        """Setup popup menu"""

        def add_action(site, url_template):
            """Build action, and connect it to a dynamically generated slot"""
            # This is not ok, Why ?
            # self.__dict__[f"open_{site}_url"] = Slot()(partial(self.open_url, url_template))

            # self.menu.addAction(
            #     self.tr(f"Search the variant on {site}"), self, SLOT(f"open_{site}_url()")
            # )

            # Method to set the slot as a instance method
            # (if we want to use it elsewhere)
            # self.__dict__[f"open_{site}_url"] = partial(self.open_url, url_template)

            self.menu.addAction(
                self.tr("Search the variant on {}").format(site),
                partial(self.open_url, url_template)
            )

        self.view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.menu = QMenu(self)
        self.menu.addAction(
            self.tr("Copy variant to clipboard"),
            self.to_clipboard
        )

        self.menu.addSeparator()

        # Built-in urls
        [add_action(*item) for item in WEBSITES_URLS.items()]

        # User urls - Get all child keys of the group databases_urls
        self.settings = QSettings()
        self.settings.beginGroup("databases_urls/")
        # Build menu actions
        [
            add_action(site, self.settings.value(site))
            for site in self.settings.childKeys()
        ]
        self.settings.endGroup()

        # Ability to trigger the menu
        self.view.customContextMenuRequested.connect(self.show_menu)

    def populate(self):
        """Show the current variant attributes on the TreeWidget"""
        # Reset
        self.view.clear()

        # Filter None values
        g = ((key, val) for key, val in self._variant.items() if val)

        for key, val in g:
            item = QTreeWidgetItem()
            item.setText(0, str(key))
            item.setText(1, str(val))
            # item.setFlags(Qt.ItemIsSelectable|Qt.ItemIsEnabled)
            # map value type to color
            item.setIcon(0, FIcon(0xF70A, TYPE_COLORS[val.__class__.__name__]))

            self.view.addTopLevelItem(item)

    def set_variant(self, variant: dict):
        """Register and show the given variant"""
        self._variant = variant
        self.populate()

    def open_url(self, url_template):
        """Search the current variant on Varsome

        .. note:: URL ex: https://varsome.com/variant/hg19/chr17-7578406-C-A
        """

        url = url_template.format(**self._variant)

        LOGGER.info("InfoVariantWidget:search_on_varsome:: Open <%s>" % url)
        QDesktopServices.openUrl(QUrl(url))

    @Slot()
    def to_clipboard(self):
        """Copy the current variant reference to the clipboard"""
        QApplication.clipboard().setText(
            "{chr}-{pos}-{ref}-{alt}".format(**self._variant)
        )

    def show_menu(self, pos: QPoint):
        """Show menu"""
        if not self._variant:
            return
        self.menu.popup(self.view.mapToGlobal(pos))
