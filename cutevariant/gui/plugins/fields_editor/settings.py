## ================= Settings widgets ===================
# Qt imports
from cutevariant.__main__ import main
import json
from cutevariant.gui.plugins.fields_editor.widgets import FieldsPresetModel
from cutevariant.gui.plugins.harmonizome_wordset import dialogs
from typing import List
from PySide2.QtCore import *
from PySide2.QtGui import QColor, QFont, QIcon, QKeySequence, QPixmap
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

        self.label_description = QLabel(
            self.tr(
                """In this settings page, you can see the list of field presets. If you need to, you can rename or remove them.
To create new presets, hit the save button in the fields editor"""
            ),
            self,
        )

        self.le_presets_file = QLineEdit(self)
        self.le_presets_file.setPlaceholderText(self.tr("Presets file"))
        self.open_preset_act = self.le_presets_file.addAction(
            FIcon(0xF0DCF), QLineEdit.TrailingPosition
        )
        self.open_preset_act.triggered.connect(self._on_open_preset_file)

        self.presets_view = QListView(self)
        self.presets_model = FieldsPresetModel(self)
        self.presets_view.setModel(self.presets_model)

        self.delete_preset_action = QAction(self.tr("Delete preset"), self)
        self.delete_preset_action.setShortcut(QKeySequence.Delete)
        # Call model's remove preset with currently displayed preset name
        self.delete_preset_action.triggered.connect(
            lambda: self.presets_model.rem_preset(
                self.presets_view.currentIndex().data(Qt.DisplayRole)
            )
        )
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
        main_layout.addWidget(self.le_presets_file)
        main_layout.addWidget(self.presets_view)

    def save(self):
        config: Config = self.section_widget.create_config()
        if os.path.isfile(self.le_presets_file.text()):
            config["presets_path"] = self.le_presets_file.text()
        else:
            # Choose this as the default (undefined) preset path. This way there
            config["presets_path"] = self.presets_model.default_path

        self.presets_model.save()
        config.save()

    def load(self):
        config = self.section_widget.create_config()

        presets_path = config.get("presets_path", self.presets_model.default_path)
        self.le_presets_file.setText(presets_path)

        self.presets_model.filename = presets_path
        self.presets_model.load()

    def _on_open_preset_file(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self, self.tr("Please choose a presets file"), QDir.homePath()
        )
        if file_name and os.path.isfile(file_name):
            self.presets_model.clear()
            self.presets_model.filename = file_name
            self.presets_model.load()


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
