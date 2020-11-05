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

        help_label = QLabel(self.tr(
            "Allow to set predefined masks for urls pointing to various databases of variants.\n"
            "Shortcuts will be visible from contextual menu over current variant."
        ))

        self.view = QListWidget()
        self.add_button = QPushButton(self.tr("Add"))
        self.edit_button = QPushButton(self.tr("Edit"))
        self.set_default_button = QPushButton(self.tr("Set default"))
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
        self.set_default_button.clicked.connect(self.load_default_external_links)
        self.remove_button.clicked.connect(self.remove_item)

    def save(self):
        """Override from BaseWidget"""
        settings = QSettings()

        settings.remove("plugins/variant_view/links")
        settings.beginGroup("plugins/variant_view/links")
        for i in range(self.view.count()):
            item = self.view.item(i)
            name = item.text()
            url = item.data(Qt.UserRole)
            settings.setValue(name, url)
        settings.endGroup()

    def load(self):
        """Override from BaseWidget"""
        settings = QSettings()
        settings.beginGroup("plugins/variant_view/links")
        self.view.clear()
        for key in settings.childKeys():
            self.add_list_widget_item(key, settings.value(key))

        settings.endGroup()

    def add_list_widget_item(self, db_name: str, url: str):
        """Add an item to the QListWidget of the current view"""
        # Key is the name of the database, value is its url
        item = QListWidgetItem(db_name)
        item.setIcon(FIcon(0xF0866))
        item.setData(Qt.UserRole, str(url))
        item.setToolTip(str(url))
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
        settings.beginGroup("plugins/variant_view/links")

        for db_name, db_url in cm.WEBSITES_URLS.items():
            self.add_list_widget_item(db_name, db_url)

        settings.endGroup()


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
