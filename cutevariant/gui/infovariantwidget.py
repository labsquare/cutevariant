"""Plugin to show all characteristics of a selected variant

InfoVariantWidget is showed on the GUI, it uses VariantPopupMenu to display a
contextual menu about the variant which is selected.
VariantPopupMenu is also used in viewquerywidget for the same purpose.
"""
# Standard imports
from functools import partial

# Qt imports
from PySide2.QtCore import Qt, QPoint, QSettings, QUrl
from PySide2.QtWidgets import *
from PySide2.QtGui import QDesktopServices

# Custom imports
from .plugin import VariantPluginWidget
from cutevariant.gui.settings import SettingsWidget
from cutevariant.gui.ficon import FIcon
from cutevariant.gui.style import TYPE_COLORS
from cutevariant.commons import logger, WEBSITES_URLS

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


class InfoVariantWidget(VariantPluginWidget):
    """Plugin to show all characteristics of a selected variant"""

    def __init__(self):
        super().__init__()

        self.setWindowTitle(self.tr("Info variants"))

        # Set columns of TreeWidget
        self.view = QTreeWidget()
        self.view.setColumnCount(2)
        # Set title of columns
        self.view.setHeaderLabels([self.tr("Attributes"), self.tr("Values")])

        v_layout = QVBoxLayout()
        v_layout.setContentsMargins(0, 0, 0, 0)
        v_layout.addWidget(self.view)
        self.setLayout(v_layout)

        # Create menu
        self.context_menu = VariantPopupMenu()
        # Ability to trigger the menu
        self.view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.view.customContextMenuRequested.connect(self.show_menu)

        self._variant = dict()

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
        """Register and show the given variant
        Called when a user clicks on a vriant on the ViewQueryWidget"""
        self._variant = variant
        self.populate()

    def show_menu(self, pos: QPoint):
        """Show context menu associated to the current variant"""
        if not self._variant:
            return
        self.context_menu.popup(self._variant, self.view.mapToGlobal(pos))
