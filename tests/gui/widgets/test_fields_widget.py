from cutevariant.gui.widgets import FieldsModel, FieldsWidget
from cutevariant.core import sql
from tests import utils


def test_model(qtmodeltester):
    conn = utils.create_conn()
    model = FieldsModel(conn)

    assert model.rowCount() == 0

    model.load()

    assert (
        model.rowCount()
        == conn.execute("SELECT COUNT(*) FROM fields WHERE category != 'samples'").fetchone()[0]
    )

    expected_fields = ["chr", "pos"]
    model.set_fields(expected_fields)
    assert model.get_fields() == expected_fields

    qtmodeltester.check(model)


def test_filter_widget(qtbot):

    conn = utils.create_conn()
    widget = FieldsWidget(conn)
    qtbot.addWidget(widget)

    widget.load()

    expected_fields = ["chr", "pos"]
    widget.set_fields(expected_fields)
    assert widget.get_fields() == expected_fields
