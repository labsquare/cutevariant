# Standard imports
import pytest

# Qt imports
from PySide2 import QtCore, QtWidgets

# Custom imports
from tests import utils
from cutevariant.gui.plugins.word_set import widgets


WORD_FILE = "examples/gene.txt"


@pytest.fixture
def conn():
    return utils.create_conn()


def test_wordset_dialog(qtbot):

    dialog = widgets.WordListDialog()
    dialog.show()

    # Add 2 items
    qtbot.mouseClick(dialog.add_button, QtCore.Qt.LeftButton)

    assert dialog.model.rowCount() == 1

    # Select first item
    dialog.view.setCurrentIndex(dialog.model.index(0, 0))
    qtbot.mouseClick(dialog.del_button, QtCore.Qt.LeftButton)
    assert dialog.model.rowCount() == 0

    # Load  from file
    dialog.load_file(WORD_FILE)

    # count word file
    with open(WORD_FILE) as file:
        word_count = len(file.readlines())
    assert dialog.model.rowCount() == word_count

    # Delete all
    dialog.view.selectAll()
    qtbot.mouseClick(dialog.del_button, QtCore.Qt.LeftButton)
    assert dialog.model.rowCount() == 0


def test_wordset_plugin(qtbot, conn):

    w = widgets.WordSetWidget()
