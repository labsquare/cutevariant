from cutevariant.gui.widgets import SamplesEditor, SamplesEditorModel
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QKeySequence

from tests import utils


def test_model(qtmodeltester):

    conn = utils.create_conn()
    model = SamplesEditorModel(conn)

    assert model.rowCount() == 0
    # Load samples
    model.load()
    sample_count = conn.execute("SELECT COUNT(*) FROM samples").fetchone()[0]
    assert model.rowCount() == sample_count

    qtmodeltester.check(model)


def test_widget(qtbot):
    conn = utils.create_conn()

    widget = SamplesEditor(conn)
    qtbot.addWidget(widget)

    # Select NORMAL
    index = widget.model.index(0, 0)
    assert index.data() == "NORMAL"

    widget.view.setCurrentIndex(index)

    with qtbot.waitSignal(widget.sample_selected, timeout=100) as blocker:
        qtbot.mouseClick(widget.btn_box.buttons()[0], Qt.LeftButton)

        assert blocker.args[0] == ["NORMAL"]
