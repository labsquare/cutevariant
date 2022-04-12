from tests import utils
import pytest
import tempfile
import os

# Qt imports

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

from tests import utils


from cutevariant.gui.widgets import project_wizard as wz


def test_create_project(qtbot):

    prj = wz.ProjectWizard()

    qtbot.addWidget(prj)

    prj.show()
    prj.hide()
    folder_path = tempfile.mkdtemp()
    assert type(prj.currentPage()) == wz.ProjectPage

    prj.currentPage().name_edit.setText("test_project")
    prj.currentPage().path_edit.setText(folder_path)

    #  Second page
    prj.next()
    assert type(prj.currentPage()) == wz.FilePage
    vcf_file = "examples/test.snpeff.vcf.gz"
    assert os.path.exists(vcf_file)
    prj.currentPage().widget.set_filename("examples/test.snpeff.vcf.gz")

    # # Third page

    # # last page
    print(prj.page(2))
    with qtbot.waitSignal(prj.page(2).completeChanged, timeout=10000):
        prj.next()

    prj.close()

    # # Check if project has been created

    assert os.path.exists(f"{folder_path}/test_project.db")
