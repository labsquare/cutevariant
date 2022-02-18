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
    assert len(plugin.widget_fields.views[0]["model"].checked_fields()) == 2
    assert len(plugin.widget_fields.views[1]["model"].checked_fields()) == 2
    assert len(plugin.widget_fields.views[2]["model"].checked_fields()) == 2


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

    print("ICI", model._presets)
    assert model.rowCount() == 2

    qtmodeltester.check(model)

    os.remove(filename)


def test_preset_dialog(conn, qtbot):

    w = widgets.PresetsDialog("test_preset")

    qtbot.addWidget(w)

    fields = ["chr", "pos", "ref", "alt", "ann.gene", "ann.impact"]
    w.fields = fields

    # Test moving fields ...
    w.view.setCurrentRow(0)
    w.move_down()
    assert w.fields == ["pos", "chr", "ref", "alt", "ann.gene", "ann.impact"]

    w.view.setCurrentRow(1)
    w.move_up()
    assert w.fields == ["chr", "pos", "ref", "alt", "ann.gene", "ann.impact"]

    w.view.setCurrentRow(5)
    [w.move_up() for i in range(5)]
    assert w.fields == ["ann.impact", "chr", "pos", "ref", "alt", "ann.gene"]


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

    # check field checked is not emit
    with qtbot.assertNotEmitted(model.field_checked):
        model.load()

    fields = ["chr", "pos", "ref"]

    with qtbot.assertNotEmitted(model.field_checked):
        model.set_checked_fields(fields)

    assert model.checked_fields() == fields

    for item in model.checked_items():
        assert item.text() in fields

    # check comment item
    with qtbot.waitSignal(model.field_checked, timeout=10000) as blocker:
        model.item(1).setCheckState(QtCore.Qt.Checked)

    assert blocker.args == ["comment", True]

    assert len(model.checked_fields()) == 4


def test_fields_widget(conn, qtbot):
    widget = widgets.FieldsWidget()
    widget.conn = conn
    widget.fields = ["chr", "pos"]
    assert widget.fields == ["chr", "pos"]
