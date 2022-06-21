## ================= Settings widgets ===================
# Qt imports
from typing import List
from PySide6.QtGui import QColor, QFont, QIcon, QPixmap
from PySide6.QtWidgets import QFormLayout, QComboBox

# Custom imports
from cutevariant.gui.plugin import PluginSettingsWidget
from cutevariant.gui.settings import AbstractSettingsWidget
from cutevariant.gui import FIcon
import cutevariant.constants as cst
from cutevariant.config import Config

from cutevariant.gui.widgets import ClassificationEditor

from cutevariant import LOGGER

import typing
import copy


class GeneralSettings(AbstractSettingsWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(self.tr("General"))
        self.setWindowIcon(FIcon(0xF070F))

        # Classification
        classifications = Config("classifications")
        classifications_genotypes = classifications.get("genotypes", [])
        self.classifications_genotypes_dict = {
            classification["name"]: classification["number"]
            for classification in classifications_genotypes
        }
        self.classifications_genotypes_dict_inv = {
            classification["number"]: classification["name"]
            for classification in classifications_genotypes
        }
        self.classifications_genotypes_list = list(self.classifications_genotypes_dict)
 
        self.classifications_combobox = QComboBox()

        f_layout = QFormLayout(self)
        f_layout.addRow(self.tr("Default Classification"), self.classifications_combobox)

    def save(self):
        config = self.section_widget.create_config()

        # Classification
        config["default_classification_validation"] = self.classifications_genotypes_dict.get(self.classifications_combobox.currentText(),0)
        
        config.save()

    def load(self):

        # Classification
        self.classifications_combobox.clear()
        self.classifications_combobox.addItems(self.classifications_genotypes_list)
        config = Config("genotypes")
        classification = config.get("default_classification_validation", 0)
        classification_name = self.classifications_genotypes_dict_inv.get(classification, "unknown")
        try:
            classification_index = self.classifications_genotypes_list.index(classification_name)
            self.classifications_combobox.setCurrentIndex(classification_index)
        except ValueError:
            LOGGER.debug("Genotypes Classification not found")
        


class GenotypesSettingsWidget(PluginSettingsWidget):
    """Instantiated plugin in the settings panel of Cutevariant

    Allow users to set predefined masks for urls pointing in various databases
    of variants.
    """

    ENABLE = True

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowIcon(FIcon(0xF0AA1))
        self.setWindowTitle("Genotypes")
        self.add_page(GeneralSettings())

