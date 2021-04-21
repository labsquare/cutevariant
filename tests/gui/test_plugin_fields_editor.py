from tests import utils
import pytest
import tempfile

# Qt imports
from PySide2 import QtCore, QtWidgets, QtGui

from tests import utils


from cutevariant.gui.plugins.fields_editor import widgets
from cutevariant.core import sql


@pytest.fixture
def conn():
    return utils.create_conn()


TEST_FIELDS = [
    (
        # Test check annotation fields
        ["chr", "pos", "ref", "alt"],
        ["ann.gene", "ann.impact"],
        ["chr", "pos", "ref", "alt", "ann.gene", "ann.impact"],
    ),
    (
        # Test check when plugin is initialized with no fields
        [],
        ["ann.gene", "ann.impact"],
        ["ann.gene", "ann.impact"],
    ),
    (
        # Test check sample fields
        ["chr", "pos", "ref", "alt"],
        ["samples.NORMAL.gt", "samples.TUMOR.gt"],
        ["chr", "pos", "ref", "alt", "samples.NORMAL.gt", "samples.TUMOR.gt"],
    ),
]


def test_plugin(conn, qtbot):
    plugin = widgets.FieldsEditorWidget()
    plugin.conn = conn
    plugin.show()


# def test_model_load(qtmodeltester, conn):

#     model = widgets.FieldsModel()
#     model.conn = conn
#     model.load()
#     qtmodeltester.check(model)

#     #  check categories
#     assert model.item(0).text() == "variants"
#     assert model.item(1).text() == "annotations"
#     assert model.item(2).text() == "samples"

#     #  Check first element of the variants ( should be favorite)
#     assert model.item(0).child(0).text() == "favorite"

#     #  test uncheck
#     assert model.item(0).child(0).checkState() == QtCore.Qt.Unchecked
#     assert model.checked_fields == []

#     # test check
#     model.item(0).child(0).setCheckState(QtCore.Qt.Checked)
#     assert model.checked_fields == ["favorite"]

#     # Test serialisation
#     _, file = tempfile.mkstemp(suffix=".cutevariant-filter")
#     model.to_file(file)
#     # Reset model and check if it is unchecked
#     model.load()
#     assert model.item(0).child(0).checkState() == QtCore.Qt.Unchecked

#     #  Load from serialize
#     model.from_file(file)
#     assert model.item(0).child(0).checkState() == QtCore.Qt.Checked
