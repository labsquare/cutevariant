from tests import utils
import pytest
import tempfile
import os

# Qt imports

from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *

from tests import utils


from cutevariant.gui.wizards import projectwizard as wz


def test_create_project(qtbot):

    prj = wz.ProjectWizard()

    qtbot.addWidget(prj)

    prj.show()  ## Build the gui
    prj.hide()
    #  First page
    folder_path = tempfile.mkdtemp()
    assert type(prj.currentPage()) == wz.ProjectPage

    prj.currentPage().project_name_edit.setText("test_project")
    prj.currentPage().project_path_edit.setText(folder_path)

    #  Second page
    prj.next()
    assert type(prj.currentPage()) == wz.FilePage
    vcf_file = "examples/test.snpeff.vcf.gz"
    assert os.path.exists(vcf_file)
    prj.currentPage().file_path_edit.setText("examples/test.snpeff.vcf.gz")

    #  Third page
    prj.next()
    assert type(prj.currentPage()) == wz.SamplePage

    # Fourth page
    prj.next()
    assert type(prj.currentPage()) == wz.FieldsPage

    #  last page
    with qtbot.waitSignal(prj.page(4).completeChanged, timeout=10000):
        prj.next()

    prj.close()

    #  Check if project has been created

    assert os.path.exists(f"{folder_path}/test_project.db")
