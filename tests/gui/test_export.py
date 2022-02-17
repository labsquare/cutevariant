from tests import utils
import tempfile
import pytest
from cutevariant.gui import export as exp

from cutevariant.gui.plugins.variant_view import widgets
from cutevariant.core import sql
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
    sql.import_reader(conn, VcfReader("examples/test.snpeff.vcf", "snpeff"))
    return conn


@pytest.mark.parametrize("extension", ["csv", "bed", "ped", "vcf"])
def test_export_dialog(qtbot, conn, extension):

    filename = tempfile.mkstemp(suffix="." + extension)[1]
    os.remove(filename)

    dialog = exp.ExportDialogFactory.create_dialog(conn, extension, filename)

    qtbot.addWidget(dialog)
    dialog.show()
    assert dialog.isVisible()
    qtbot.mouseClick(dialog.button_box.button(QDialogButtonBox.Save), Qt.LeftButton)
    assert os.path.exists(filename), "the file has not been created"

    # print(QCoreApplication.instance().activePopupWidget())
