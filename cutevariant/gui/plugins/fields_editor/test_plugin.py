from tests import utils
import pytest
import tempfile
import os

# Qt imports
from PySide6 import QtCore, QtWidgets, QtGui

from tests import utils


from cutevariant.gui.plugins.fields_editor import widgets
from cutevariant.core import sql
from cutevariant.config import Config


@pytest.fixture
def conn():
    return utils.create_conn()


def test_plugin(conn, qtbot):
    plugin = widgets.FieldsEditorWidget()
    plugin.mainwindow = utils.create_mainwindow()
    plugin.on_open_project(conn)
