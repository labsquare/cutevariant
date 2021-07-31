# Standard imports
import json
from cutevariant.gui.plugins.fields_editor.widgets import FieldsPresetModel
from cutevariant.gui.plugins.harmonizome_wordset import dialogs
from typing import List
import os

## ================= Settings widgets ===================
# Qt imports
from PySide2.QtCore import *
from PySide2.QtGui import QColor, QFont, QIcon, QKeySequence, QPixmap
from PySide2.QtWidgets import *

# Custom imports
from cutevariant.gui.plugin import PluginSettingsWidget
from cutevariant.gui.settings import AbstractSettingsWidget
from cutevariant.gui import FIcon
import cutevariant.commons as cm
from cutevariant.config import Config

from cutevariant.gui.plugins.filters_editor.widgets import FiltersPresetModel


class PresetsSettings(AbstractSettingsWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(self.tr("Presets"))
        self.setWindowIcon(FIcon(0xF0232))

        self.label_description = QLabel(
            self.tr(
                """In this settings page, you can see the list of filter presets. If you need to, you can rename or remove them.
To create new presets, hit the save button in the filters editor"""
            ),
            self,
        )

        self.presets_view = QListView(self)
        self.presets_model = FiltersPresetModel(parent=self)
        self.presets_view.setModel(self.presets_model)

        self.delete_preset_action = QAction(self.tr("Delete preset"), self)
        self.delete_preset_action.setShortcut(QKeySequence.Delete)
        # Call model's remove preset with currently displayed preset name
        self.delete_preset_action.triggered.connect(self._on_remove_presets)
        self.presets_view.addAction(self.delete_preset_action)

        self.rename_preset_action = QAction(self.tr("Rename preset"), self)
        self.rename_preset_action.triggered.connect(
            lambda: self.presets_view.edit(self.presets_view.currentIndex())
        )
        self.presets_view.addAction(self.rename_preset_action)

        self.presets_view.setContextMenuPolicy(Qt.ActionsContextMenu)
        self.presets_view.setSelectionMode(QAbstractItemView.ExtendedSelection)

        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.label_description)
        main_layout.addWidget(self.presets_view)

    def save(self):
        self.presets_model.save()

    def load(self):
        self.presets_model.load()

    def _on_remove_presets(self):
        """Remove all selected presets in the view"""
        self.presets_model.rem_presets(
            [idx.row() for idx in self.presets_view.selectionModel().selectedRows()]
        )


class FiltersEditorSettingsWidget(PluginSettingsWidget):
    """Instantiated plugin in the settings panel of Cutevariant

    Allow users to set predefined masks for urls pointing in various databases
    of variants.
    """

    ENABLE = True

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowIcon(FIcon(0xF0232))
        self.setWindowTitle("Filters editor")
        self.add_page(PresetsSettings())
