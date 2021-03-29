from tests import utils
import tempfile
import pytest
from cutevariant.gui import export as exp

from cutevariant.gui.plugins.variant_view import widgets
from cutevariant.core import sql, importer
from cutevariant.core.reader import VcfReader

import os
from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *


@pytest.fixture
def conn():
    #  Required a real file to make it work !
    tempdb = tempfile.mkstemp(suffix=".db")[1]
    conn = sql.get_sql_connection(tempdb)
    importer.import_reader(conn, VcfReader(open("examples/test.snpeff.vcf"), "snpeff"))
    return conn


def test_export_csv(qtbot, conn):

    filename = tempfile.mkstemp(suffix=".csv")[1]
    os.remove(filename)

    dialog = exp.ExportDialogFactory.create_dialog(conn, "CSV")
    assert isinstance(dialog, exp.CsvExportDialog)
    qtbot.addWidget(dialog)
    dialog.show()
    assert dialog.isVisible()

    qtbot.mouseClick(dialog.button_box.button(QDialogButtonBox.Save), Qt.LeftButton)

    assert os.path.exists(filename), "the file has not been created"

    qtbot.mouseClick(dialog.button_box.button(QDialogButtonBox.Cancel), Qt.LeftButton)
    assert not dialog.isVisible()


def test_export_vcf(qtbot, conn):
    pass
