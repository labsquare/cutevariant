## ================= Settings widgets ===================
# Qt imports
from cutevariant.gui.plugins.fields_editor.widgets import FieldsPresetModel
from cutevariant.gui.plugins.harmonizome_wordset import dialogs
from typing import List
from PySide2.QtCore import *
from PySide2.QtGui import QColor, QFont, QIcon, QPixmap
from PySide2.QtWidgets import *

# Custom imports
from cutevariant.gui.plugin import PluginSettingsWidget
from cutevariant.gui.settings import AbstractSettingsWidget
from cutevariant.gui import FIcon
import cutevariant.commons as cm
from cutevariant.config import Config

from cutevariant.gui.plugins.fields_editor.widgets import FieldsPresetModel

import typing
import copy
import os


class GeneralSettings(AbstractSettingsWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(self.tr("General"))
        self.setWindowIcon(FIcon(0xF08DF))

        self.presets_view = QListView(self)

        main_layout = QVBoxLayout(self)

    def save(self):
        config = self.section_widget.create_config()
        config.save()

    def load(self):
        config = self.section_widget.create_config()


class FieldsEditorSettingsWidget(PluginSettingsWidget):
    """Instantiated plugin in the settings panel of Cutevariant

    Allow users to set predefined masks for urls pointing in various databases
    of variants.
    """

    ENABLE = True

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowIcon(FIcon(0xF08DF))
        self.setWindowTitle("Fields editor")
        self.add_page(GeneralSettings())
