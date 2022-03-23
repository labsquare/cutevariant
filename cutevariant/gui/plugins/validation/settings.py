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
import cutevariant.commons as cm
from cutevariant.config import Config

from cutevariant.gui.widgets import TagEditor

import typing
import copy


class SampleTagSettings(AbstractSettingsWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(self.tr("Sample tags"))
        self.setWindowIcon(FIcon(0xF070F))

        self.editor = TagEditor()
        v_layout = QVBoxLayout(self)
        v_layout.addWidget(self.editor)

    def save(self):
        """overload"""
        config = self.section_widget.create_config()
        config["sample_tags"] = self.editor.get_tags()
        config.save()

    def load(self):
        """Overload"""
        config = self.section_widget.create_config()
        tags = config.get("sample_tags", "")
        self.editor.set_tags(tags)

class ValidationTagSettings(AbstractSettingsWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(self.tr("Validation tags"))
        self.setWindowIcon(FIcon(0xF070F))

        self.editor = TagEditor()
        v_layout = QVBoxLayout(self)
        v_layout.addWidget(self.editor)

    def save(self):
        """overload"""
        config = self.section_widget.create_config()
        config["validation_tags"] = self.editor.get_tags()
        config.save()

    def load(self):
        """Overload"""
        config = self.section_widget.create_config()
        tags = config.get("validation_tags", "")
        self.editor.set_tags(tags)


class ValidationSettingsWidget(PluginSettingsWidget):
    """Instantiated plugin in the settings panel of Cutevariant

    Allow users to set predefined masks for urls pointing in various databases
    of variants.
    """

    ENABLE = True

    def __init__(self, parent=None):
        super().__init__(parent)

        self.add_page(ValidationTagSettings())
        self.add_page(SampleTagSettings())
