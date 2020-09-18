## ================= Settings widgets ===================

from cutevariant.gui.plugin import PluginSettingsWidget
from cutevariant.gui.settings import BaseWidget
from cutevariant.gui import FIcon

from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWidgets import *


class LinkSettings(BaseWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(self.tr("Link"))
        self.setWindowIcon(FIcon(0xF339))
        self.view = QListWidget()
        self.add_button = QPushButton(self.tr("Add"))
        self.edit_button = QPushButton(self.tr("Edit"))
        self.remove_button = QPushButton(self.tr("Remove"))

        v_layout = QVBoxLayout()
        v_layout.addWidget(self.add_button)
        v_layout.addWidget(self.edit_button)
        v_layout.addStretch()
        v_layout.addWidget(self.remove_button)

        main_layout = QHBoxLayout()
        main_layout.addWidget(self.view)
        main_layout.addLayout(v_layout)

        self.setLayout(main_layout)

        # Signals
        self.add_button.clicked.connect(self.add_url)
        self.edit_button.clicked.connect(self.edit_item)
        self.view.itemDoubleClicked.connect(self.add_url)
        self.remove_button.clicked.connect(self.remove_item)

    def save(self):
        """Override from BaseSettings """
        settings = QSettings()

        settings.remove("plugins/query_view/links")
        settings.beginGroup("plugins/query_view/links")
        for i in range(self.view.count()):
            item = self.view.item(i)
            name = item.text()
            url = item.data(Qt.UserRole)
            settings.setValue(name, url)
        settings.endGroup()

    def load(self):
        """Override from BaseSettings """
        settings = QSettings()
        settings.beginGroup("plugins/query_view/links")
        self.view.clear()
        for key in settings.childKeys():
            self.add_list_widget_item(key, settings.value(key))

        settings.endGroup()

    def add_list_widget_item(self, db_name: str, url: str):
        """Add an item to the QListWidget of the current view"""
        # Key is the name of the database, value is its url
        item = QListWidgetItem(db_name)
        item.setIcon(FIcon(0xF339))
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
        title = QLabel("example: http://url_with_columns{chr}{pos}{ref}{alt}")
        name = QLineEdit()
        url = QLineEdit()
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout = QFormLayout()
        layout.addWidget(title)
        layout.addRow(self.tr("Name"), name)
        layout.addRow(self.tr("Url"), url)
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


class QueryViewSettingsWidget(PluginSettingsWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowIcon(FIcon(0xF503))
        self.setWindowTitle("Variant view")
        self.add_settings_widget(LinkSettings())
