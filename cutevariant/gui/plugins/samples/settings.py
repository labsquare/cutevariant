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


class ClassificationSettings(AbstractSettingsWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(self.tr("Classification"))
        # self.setWindowIcon(FIcon(0xF070F))

        layout = QVBoxLayout(self)
        self.w = ClassificationEditor()
        layout.addWidget(self.w)

    def save(self):
        """override"""
        config = self.section_widget.create_config()
        config["classifications"] = self.w.get_classifications()
        config.save()

    def load(self):
        """override"""
        config = self.section_widget.create_config()
        classifications = config.get("classifications", [])
        self.w.set_classifications(classifications)


class SamplesSettingsWidget(PluginSettingsWidget):
    """Instantiated plugin in the settings panel of Cutevariant

    Allow users to set predefined masks for urls pointing in various databases
    of variants.
    """

    ENABLE = True

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowIcon(FIcon(0xF035C))
        self.setWindowTitle("Samples")
        self.add_page(ClassificationSettings())
