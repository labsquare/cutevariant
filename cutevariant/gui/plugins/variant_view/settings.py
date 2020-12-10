## ================= Settings widgets ===================
# Qt imports
from PySide2.QtCore import *
from PySide2.QtWidgets import *

# Custom imports
from cutevariant.gui.plugin import PluginSettingsWidget
from cutevariant.gui.settings import BaseWidget
from cutevariant.gui import FIcon
import cutevariant.commons as cm


class LinkSettings(BaseWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(self.tr("Cross databases links"))
        self.setWindowIcon(FIcon(0xF070F))

        help_label = QLabel(
            self.tr(
                "Allow to set predefined masks for urls pointing to various databases of variants.\n"
                "Shortcuts will be visible from contextual menu over current variant.\n"
                "Set a link as default makes possible to open alink by double clicking on the view."
            )
        )

        self.view = QListWidget()
        self.add_button = QPushButton(self.tr("Add"))
        self.edit_button = QPushButton(self.tr("Edit"))
        self.set_default_button = QPushButton(self.tr("Set as default"))
        self.set_default_button.setToolTip(self.tr("Double click will open this link"))
        self.remove_button = QPushButton(self.tr("Remove"))

        v_layout = QVBoxLayout()
        v_layout.addWidget(self.add_button)
        v_layout.addWidget(self.edit_button)
        v_layout.addStretch()
        v_layout.addWidget(self.set_default_button)
        v_layout.addWidget(self.remove_button)

        h_layout = QHBoxLayout()
        h_layout.addWidget(self.view)
        h_layout.addLayout(v_layout)

        main_layout = QVBoxLayout()
        main_layout.addWidget(help_label)
        main_layout.addLayout(h_layout)
        self.setLayout(main_layout)

        # Signals
        self.add_button.clicked.connect(self.add_url)
        self.edit_button.clicked.connect(self.edit_item)
        self.view.itemDoubleClicked.connect(self.add_url)
        self.set_default_button.clicked.connect(self.set_default_link)
        self.remove_button.clicked.connect(self.remove_item)

    def save(self):
        """Override from BaseWidget"""
        settings = QSettings()
        # Bug from Pyside2.QSettings which don't return boolean
        settings.remove("plugins/variant_view/links")
        settings.beginWriteArray("plugins/variant_view/links")
        for i in range(self.view.count()):
            settings.setArrayIndex(i)
            item = self.view.item(i)
            name = item.text()
            url = item.data(Qt.UserRole)
            is_default = int(item.data(Qt.UserRole + 1))
            settings.setValue("name", name)
            settings.setValue("url", url)
            settings.setValue("is_default", is_default)
        settings.endArray()

    def load(self):
        """Override from BaseWidget"""
        settings = QSettings()
        size = settings.beginReadArray("plugins/variant_view/links")
        self.view.clear()

        #  If no links available, load default one
        # if size == 0:
        #     self.load_default_external_links()

        for i in range(size):
            settings.setArrayIndex(i)
            name = settings.value("name")
            url = settings.value("url")

            # Bug from Pyside2.QSettings which don't return boolean
            is_default = bool(int(settings.value("is_default")))
            self.add_list_widget_item(name, url, is_default)
        settings.endArray()

    def add_list_widget_item(self, db_name: str, url: str, is_default=False):
        """Add an item to the QListWidget of the current view"""
        # Key is the name of the database, value is its url
        item = QListWidgetItem(db_name)
        item.setIcon(FIcon(0xF0866))
        item.setData(Qt.UserRole, str(url))  #  UserRole = Link
        item.setData(Qt.UserRole + 1, bool(is_default))  # UserRole+1 = is default link
        item.setToolTip(str(url))

        font = item.font()
        font.setBold(is_default)
        item.setFont(font)

        self.view.addItem(item)

    def edit_list_widget_item(self, item: QListWidgetItem, db_name: str, url: str):
        """Modify the given item"""
        item.setText(db_name)
        item.setData(Qt.UserRole, url)

    def add_url(self, item=None):
        """Allow the user to insert and save custom database URL"""
        # Display dialog box to let the user enter it's own url
        dialog = QDialog()
        title = QLabel(self.tr("Example: http://url_with_columns{chr}{pos}{ref}{alt}"))
        name = QLineEdit()
        url = QLineEdit()
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout = QFormLayout()
        layout.addWidget(title)
        layout.addRow(self.tr("Name"), name)
        layout.addRow(self.tr("Url mask"), url)
        layout.addWidget(buttons)

        dialog.setLayout(layout)

        if item:
            # Called by itemDoubleClicked or edit_item
            # Fill forms with item data
            name.setText(item.text())
            url.setText(item.data(Qt.UserRole))

        # Also do a minimal check on the data inserted
        if dialog.exec_() == QDialog.Accepted and name.text() and url.text():

            if item:
                # Edit the current item in the list
                self.edit_list_widget_item(item, name.text(), url.text())
            else:
                # Add the item to the list
                self.add_list_widget_item(name.text(), url.text())

            # Save the item in settings
            # (Here to limit the friction with Save all button)

    def edit_item(self):
        """Edit the selected item

        .. note:: This function uses add_url to display the edit window
        """
        # Get selected item
        # Always use the first selected item returned
        self.add_url(self.view.selectedItems()[0])

    def remove_item(self):
        """Remove the selected item

        .. todo:: removeItemWidget() is not functional?
        """
        # Get selected item
        item = self.view.selectedItems()[0]

        # Delete the item
        self.view.takeItem(self.view.row(item))
        del item  # Is it mandatory in Python ?

    def load_default_external_links(self):
        """Load default external DB links"""
        settings = QSettings()
        settings.beginWriteArray("plugins/variant_view/links")

        for index, item in enumerate(cm.WEBSITES_URLS.items()):
            settings.settings.setArrayIndex(index)
            db_name, db_url = item
            is_default = False if index else True
            self.add_list_widget_item(db_name, db_url, is_default)

        settings.endArray()

    def set_default_link(self):
        """ set current item as default link """
        current_item = self.view.currentItem()

        for row in range(self.view.count()):
            item = self.view.item(row)
            font = item.font()
            is_default = True if item == current_item else False
            item.setData(Qt.UserRole + 1, is_default)
            font.setBold(is_default)
            item.setFont(font)


class VariantViewSettingsWidget(PluginSettingsWidget):
    """Instantiated plugin in the settings panel of Cutevariant

    Allow users to set predefined masks for urls pointing in various databases
    of variants.
    """

    ENABLE = True

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowIcon(FIcon(0xF035C))
        self.setWindowTitle("Variant view")
        self.add_settings_widget(LinkSettings())
