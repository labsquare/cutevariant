from tests import utils
import pytest
import tempfile
import os

# Qt imports
from PySide2 import QtCore, QtWidgets, QtGui

from tests import utils


from cutevariant.gui.plugins.fields_editor import widgets
from cutevariant.core import sql
from cutevariant.config import Config


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

    fields = [
        "chr",
        "pos",
        "ann.gene",
        "ann.impact",
        "samples.TUMOR.gt",
        "samples.NORMAL.gt",
    ]
    plugin.widget_fields.fields = fields
    assert len(plugin.widget_fields.views[0]["model"].fields) == 2
    assert len(plugin.widget_fields.views[1]["model"].fields) == 2
    assert len(plugin.widget_fields.views[2]["model"].fields) == 2


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


def test_preset_dialog(conn, qtbot):

    w = widgets.PresetsDialog("test_preset")

    qtbot.addWidget(w)
    config = Config("fields_editor")
    preset = {"test_preset": ["chr", "pos", "ref", "alt", "ann.gene"]}
    config["presets"] = preset
    config.save()

    w.load()

    assert sorted(w.fields) == sorted(preset["test_preset"])

    # Add extra fields and save
    w.fields += ["ann.impact"]
    w.save()

    # Load config to see if the saving has occurs
    config.load()
    assert config["presets"]["test_preset"] == preset["test_preset"] + ["ann.impact"]

    # Test moving fields ...
    w.view.setCurrentRow(0)
    w.move_down()
    assert w.fields == ["pos", "chr", "ref", "alt", "ann.gene", "ann.impact"]

    w.view.setCurrentRow(5)
    [w.move_up() for i in range(5)]
    assert w.fields == ["ann.impact", "pos", "chr", "ref", "alt", "ann.gene"]

    del config["presets"]["test_preset"]
    config.save()


def test_fields_model(qtmodeltester, conn, qtbot):

    model = widgets.FieldsModel()
    model.conn = conn

    # Load variant categories
    model.category = "variants"
    model.load()
    assert model.rowCount() == len(sql.get_field_by_category(conn, model.category))

    # Load annotations categories
    model.category = "annotations"
    model.load()
    assert model.rowCount() == len(sql.get_field_by_category(conn, model.category))

    # Load samples categories ! Not ( you must repeat fields per samples)
    model.category = "samples"
    model.load()
    sample_count = len(list(sql.get_samples(conn)))
    fields_count = len(sql.get_field_by_category(conn, model.category))
    assert model.rowCount() == sample_count * fields_count

    # check fields
    model.category = "variants"
    model.load()

    fields = ["chr", "pos", "ref"]
    model.fields = fields

    for item in model.get_checked_items():
        assert item.text() in fields

    # check item 20
    assert len(model.fields) == 3

    with qtbot.waitSignal(model.fields_changed, timeout=10000) as blocker:
        model.item(1).setCheckState(QtCore.Qt.Checked)

    assert len(model.fields) == 4

    # #  check categories
    # assert model.item(0).text() == "variants"
    # assert model.item(1).text() == "annotations"
    # assert model.item(2).text() == "samples"

    # #  Check first element of the variants ( should be favorite)
    # assert model.item(0).child(0).text() == "favorite"

    # #  test uncheck
    # assert model.item(0).child(0).checkState() == QtCore.Qt.Unchecked
    # assert model.checked_fields == []

    # # test check
    # model.item(0).child(0).setCheckState(QtCore.Qt.Checked)
    # assert model.checked_fields == ["favorite"]

    # # Test serialisation
    # _, file = tempfile.mkstemp(suffix=".cutevariant-filter")
    # model.to_file(file)
    # # Reset model and check if it is unchecked
    # model.load()
    # assert model.item(0).child(0).checkState() == QtCore.Qt.Unchecked

    # #  Load from serialize
    # model.from_file(file)
    # assert model.item(0).child(0).checkState() == QtCore.Qt.Checked
