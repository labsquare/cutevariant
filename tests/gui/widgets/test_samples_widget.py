from cutevariant.gui.widgets import SamplesWidget, SamplesModel
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QKeySequence

from tests import utils


def test_model(qtmodeltester):

    conn = utils.create_conn()
    model = SamplesModel(conn)

    assert model.rowCount() == 0
    # Load samples
    model.load()
    sample_count = conn.execute("SELECT COUNT(*) FROM samples").fetchone()[0]
    assert model.rowCount() == sample_count

    qtmodeltester.check(model)


def test_widget(qtbot):
    conn = utils.create_conn()

    widget = SamplesWidget(conn)
    assert len(widget.get_selected_samples()) == 0

    # Test duplicate skiping
    widget.set_selected_samples(["TUMOR"])
    assert len(widget.get_selected_samples()) == 1
    widget.set_selected_samples(["TUMOR"])
    assert len(widget.get_selected_samples()) == 1
    widget.set_selected_samples(["NORMAL"])
    assert len(widget.get_selected_samples()) == 2
