## ================= Settings widgets ===================
# Qt imports
from typing import List
from PySide6.QtCore import *
from PySide6.QtGui import QColor, QFont, QIcon, QPixmap
from PySide6.QtWidgets import *

# Custom imports
from cutevariant.gui.plugin import PluginSettingsWidget
from cutevariant.gui.settings import AbstractSettingsWidget
from cutevariant.gui import FIcon
import cutevariant.constants as cst
from cutevariant.config import Config

from cutevariant.gui.widgets import ClassificationEditor


import typing
import copy


class LinksModel(QAbstractListModel):
    def __init__(self) -> None:
        super().__init__()
        self.links = []

    def add_link(
        self,
        name: str,
        url: str,
        is_browser: bool = True,
        is_default: bool = False,
    ) -> bool:
        """Adds a link to the model.
        Links are dictionnaries with:
            - name: How the user refers to the feature
            - url: A masked url (using curly brackets for named fields), target of the feature
            - is_browser: Whether this link will be opened with the default browser or not. If not, a single get request will be sent
            - is_default: Whether this link defines the double-click behavior in the variant view

        Args:
            name (str): The name of the link, as displayed to the user
            url (str): The target of the link. Should contain named fields in curly brackets, each name referring to a variant field name
            is_browser (bool, optional): Whether the link will be opened in the default browser. Defaults to True.
            is_default (bool, optional): Whether this link is the default one. Defaults to False.

        Returns:
            bool: True on success
        """
        if any(link["name"] == name for link in self.links):
            # If there is already a link with the same name in the model, don't add it (avoid doubles)
            return False

        new_link = {
            "name": name,
            "url": url,
            "is_browser": is_browser,
            "is_default": is_default,
        }

        # Add the new link to the model. Potentially affects current default link, so reset the whole model
        self.beginResetModel()

        self.links.append(new_link)

        # If the newly added link is set to default, make sure to put default to False for every other
        if is_default:
            for link in self.links:
                # There is a default link, but not the one we've just added
                if link["is_default"] and link is not new_link:
                    link["is_default"] = False

        self.endResetModel()
        return True

    def remove_links(self, indexes: List[QModelIndex]) -> bool:
        """Safely removes several links from a list of their indexes

        Args:
            indexes (List[QModelIndex]): List of indexes to remove

        Returns:
            bool: True on success
        """
        rows = sorted([index.row() for index in indexes], reverse=True)
        for row in rows:
            self.beginRemoveRows(QModelIndex(), row, row)
            del self.links[row]
            self.endRemoveRows()
        return True

    def remove_link(self, index: QModelIndex):
        return self.remove_links([index])

    def edit_link(
        self,
        index: QModelIndex,
        name: str,
        url: str,
        is_browser: bool,
        is_default: bool,
    ):

        edited_link = {
            "name": name,
            "url": url,
            "is_browser": is_browser,
            "is_default": is_default,
        }

        # Add the new link to the model. Potentially affects current default link, so reset the whole model
        self.beginResetModel()

        self.links[index.row()] = edited_link

        # If the newly added link is set to default, make sure to put default to False for every other
        if is_default:
            for link in self.links:
                # There is a default link, but not the one we've just added
                if link["is_default"] and link is not edited_link:
                    link["is_default"] = False

        self.endResetModel()
        return True

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self.links)

    def clear(self):
        self.beginResetModel()
        self.links.clear()
        self.endResetModel()

    def make_default(self, index: QModelIndex):
        self.beginResetModel()
        # First, set every item to 'not default'
        for link in self.links:
            link["is_default"] = False

        # And now, set default for the selected index
        self.links[index.row()]["is_default"] = True
        self.endResetModel()

    def data(self, index: QModelIndex, role: int):
        if index.row() < 0 or index.row() >= self.rowCount():
            return

        if role == Qt.DisplayRole:
            return self.links[index.row()]["name"]

        if role == Qt.ToolTipRole:
            return self.links[index.row()]["url"]

        if role == Qt.FontRole:
            font = QFont()
            if self.links[index.row()]["is_default"]:
                font.setBold(True)
                return font
            return font

        if role == Qt.UserRole:
            return self.links[index.row()]["is_default"]

        if role == Qt.UserRole + 1:
            return self.links[index.row()]["is_browser"]

        if role == Qt.DecorationRole:
            return QIcon(FIcon(0xF0866))


class GeneralSettings(AbstractSettingsWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(self.tr("General"))
        self.setWindowIcon(FIcon(0xF070F))

        self.row_count_box = QSpinBox()
        self.memory_box = QSpinBox()

        self.memory_box.setSuffix(" MB")

        self.memory_box.setRange(0, 1000)
        self.row_count_box.setRange(5, 500)

        f_layout = QFormLayout(self)
        f_layout.addRow(self.tr("Rows per page"), self.row_count_box)
        f_layout.addRow(self.tr("Memory Cache"), self.memory_box)

    def save(self):
        config = self.section_widget.create_config()
        config["rows_per_page"] = self.row_count_box.value()
        config["memory_cache"] = self.memory_box.value()
        config.save()

    def load(self):
        config = self.section_widget.create_config()
        self.row_count_box.setValue(config.get("rows_per_page", 50))
        self.memory_box.setValue(config.get("memory_cache", 32))


class LinkSettings(AbstractSettingsWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(self.tr("External links"))
        self.setWindowIcon(FIcon(0xF070F))

        help_label = QLabel(
            self.tr(
                "Allow to set predefined masks for urls pointing to various databases of variants.\n"
                "Shortcuts will be visible from contextual menu over current variant.\n"
                "Set a link as default makes possible to open alink by double clicking on the view."
            )
        )

        self.view = QListView()
        self.link_model = LinksModel()

        self.view.setModel(self.link_model)
        self.add_button = QPushButton(self.tr("Add"))
        self.edit_button = QPushButton(self.tr("Edit"))
        self.set_default_button = QPushButton(self.tr("Set as default"))
        self.set_default_button.setToolTip(self.tr("Double click will open this link"))
        self.remove_button = QPushButton(self.tr("Remove"))

        self.batch_open_cb = QCheckBox(self.tr("Allow batch opening of all selected variants"))

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
        main_layout.addWidget(self.batch_open_cb)
        self.setLayout(main_layout)

        # Signals
        self.add_button.clicked.connect(self.add_url)
        self.edit_button.clicked.connect(self.edit_item)
        self.view.doubleClicked.connect(lambda index: self.add_url(index))
        self.set_default_button.clicked.connect(self.set_default_link)
        self.remove_button.clicked.connect(self.remove_item)

    def save(self):
        """Override from PageWidget"""

        # Bug from Pyside2.QSettings which don't return boolean
        config = self.section_widget.create_config()
        config["links"] = self.link_model.links
        config["batch_open_links"] = self.batch_open_cb.isChecked()
        config.save()

    def load(self):
        """Override from PageWidget"""
        config = self.section_widget.create_config()
        self.link_model.clear()

        if "links" in config:
            for link in config["links"]:
                self.link_model.add_link(**link)
        if "batch_open_links" in config:
            self.batch_open_cb.setChecked(bool(config["batch_open_links"]))

    def edit_item(
        self,
        index: QModelIndex,
        db_name: str,
        url: str,
        is_default=False,
        is_browser=False,
    ):
        """Modify the given item"""
        self.link_model.edit_link(index, db_name, url, is_browser, is_default)

    def add_url(self, index: QModelIndex = None):
        """Allow the user to insert and save custom database URL"""
        # Display dialog box to let the user enter it's own url
        dialog = QDialog()
        title = QLabel(
            self.tr(
                """<p>Create a link using variant fields as placeholders with <a href='https://jinja.palletsprojects.com/en/3.0.x/'>jinja2</a> syntax.<br/> 
<b>For instance: </b> <br/>
<code>https://genome.ucsc.edu/cgi-bin/hgTracks?db=hg19&position={{chr}}:{{pos}}</code><br/>
<code>https://www.google.fr?q={{annotations[0].gene}}</code><br/>
<code>https://www.google.fr?q={{chr|replace('chr','')}}</code>
 </p>
            """
            )
        )
        name = QLineEdit()
        url = QLineEdit()
        browser = QCheckBox(self.tr("Uncheck the box for http request only"))
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)

        layout = QFormLayout()
        layout.addRow(self.tr("Name"), name)
        layout.addRow(self.tr("Url mask"), url)
        layout.addRow(self.tr("Open in browser"), browser)
        layout.addWidget(buttons)

        main_layout = QVBoxLayout()
        main_layout.addWidget(title)
        main_layout.addLayout(layout)

        dialog.setLayout(main_layout)

        if index:
            # Called by itemDoubleClicked or edit_item
            # Fill forms with item data
            name.setText(index.data(Qt.DisplayRole))
            url.setText(index.data(Qt.ToolTipRole))
            is_browser = Qt.Checked if bool(index.data(Qt.UserRole + 1)) else Qt.Unchecked
            browser.setChecked(is_browser)

        # Also do a minimal check on the data inserted
        if dialog.exec_() == QDialog.Accepted and name.text() and url.text():

            if index:
                # Edit the current item in the list
                self.link_model.edit_link(
                    index, name.text(), url.text(), bool(browser.checkState()), False
                )
            else:
                # Add the item to the list
                self.link_model.add_link(name.text(), url.text(), bool(browser.checkState()), False)

            # Save the item in settings
            # (Here to limit the friction with Save all button)

    def edit_item(self):
        """Edit the selected item

        .. note:: This function uses add_url to display the edit window
        """
        # Get selected item
        # Always use the first selected item returned
        self.add_url(self.view.currentIndex())

    def remove_item(self):
        """Remove the selected item

        .. todo:: removeItemWidget() is not functional?
        """
        # Get selected rows
        if self.view.selectionModel().selectedRows():
            self.link_model.remove_links(self.view.selectionModel().selectedRows())

    def set_default_link(self):
        """set current item as default link"""

        if not self.view.currentIndex() or not self.view.currentIndex().isValid():
            return

        self.link_model.make_default(self.view.currentIndex())


class MemorySettings(AbstractSettingsWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(self.tr("Memory"))
        self.setWindowIcon(FIcon(0xF070F))

        layout = QFormLayout()
        self.spinbox = QSpinBox()
        self.spinbox.setRange(0, 100000)
        layout.addRow(self.tr("Cache size"), self.spinbox)

    def save(self):
        """overload"""
        pass

    def load(self):
        """load"""
        pass


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
        self.add_page(GeneralSettings())
        self.add_page(LinkSettings())
