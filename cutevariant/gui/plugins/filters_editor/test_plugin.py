from tests import utils
import pytest
import tempfile
import os

# Qt imports

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

from tests import utils


from cutevariant.gui.plugins.filters_editor.widgets import FiltersEditorWidget
from cutevariant.core import sql


FILTERS = {"$and": [{"gene": "chr12"}]}


def test_plugin(qtbot):

    conn = utils.create_conn()
    plugin = FiltersEditorWidget()
    plugin.mainwindow = utils.create_mainwindow()
    plugin.on_open_project(conn)
