from tests import utils
import pytest
import tempfile
import os

# Qt imports
from PySide2 import QtCore, QtWidgets, QtGui

from tests import utils


from cutevariant.gui.plugins.fields_editor import widgets
from cutevariant.core import sql


@pytest.fixture
def conn():
    return utils.create_conn()


def test_plugin(conn, qtbot):
    plugin = widgets.FieldsEditorWidget()
    plugin.on_open_project(conn)

    assert plugin.widget_fields.views[0]["model"].rowCount() == len(
        sql.get_field_by_category(conn, "variants")
    )
    assert plugin.widget_fields.views[1]["model"].rowCount() == len(
        sql.get_field_by_category(conn, "annotations")
    )
    assert plugin.widget_fields.views[2]["model"].rowCount() == len(
        sql.get_field_by_category(conn, "samples")
    ) * len(list(sql.get_samples(conn)))

    checked_fields = [
        "chr",
        "pos",
        "ann.gene",
        "ann.impact",
        "samples.TUMOR.gt",
        "samples.NORMAL.gt",
    ]
    plugin.widget_fields.checked_fields = checked_fields
    assert len(plugin.widget_fields.views[0]["model"].checked_fields) == 2
    assert len(plugin.widget_fields.views[1]["model"].checked_fields) == 2
    assert len(plugin.widget_fields.views[2]["model"].checked_fields) == 2


def test_presets_model(qtmodeltester):
    filename = tempfile.mktemp()
    model = widgets.FieldsPresetModel(config_path=filename)

    model.add_preset("preset A", ["chr", "pos", "ref"])
    model.add_preset("preset B", ["chr", "rs", "ann.gene"])
    model.add_preset("preset C", ["chr", "rs", "ann.gene", "rsid", "af"])

    assert model.rowCount() == 3

    model.rem_presets([1])
    assert model.rowCount() == 2

    model.save()

    model.clear()

    assert model.rowCount() == 0

    model.load()

    assert model.rowCount() == 2

    qtmodeltester.check(model)

    os.remove(filename)


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
