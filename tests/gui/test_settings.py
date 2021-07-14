from tests import utils
import pytest
import tempfile

# Qt imports
from PySide2.QtWidgets import *
from PySide2.QtCore import *
from cutevariant.gui import settings
from cutevariant.config import Config
import os

# Standard imports
import pytest

# Qt imports

from tests import utils


class PageTest(settings.AbstractSettingsWidget):
    def __init__(self):
        super().__init__()
        self.value = None

    def save(self):
        config = Config("test")
        config["value"] = self.value
        config.save()

    def load(self):
        config = Config("test")
        self.value = config.get("value", None)


def test_settings_dialog(qtbot):

    #  build a dialog
    dialog = settings.SettingsDialog()
    section = settings.SectionWidget()
    page = PageTest()
    section.add_page(page)
    dialog.add_section(section)

    # #  clear settings
    # page.create_settings().clear()
    # path = page.create_settings().fileName()

    qtbot.addWidget(dialog)
    dialog.show()

    page.value = 32

    #  Test Saving
    qtbot.mouseClick(dialog.button_box.button(QDialogButtonBox.SaveAll), Qt.LeftButton)

    ## is close ?
    assert not dialog.isVisible()

    ## is saved ?
    config = Config("test")

    assert config["value"] == 32

    # Test Loading
    page.value = None
    dialog.show()
    qtbot.mouseClick(dialog.button_box.button(QDialogButtonBox.Reset), Qt.LeftButton)
    assert page.value == 32
