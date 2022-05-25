from cutevariant.gui.widgets import SampleWidget
from cutevariant.core import sql
from tests import utils


def test_widget(qtbot):
    conn = utils.create_conn()

    widget = SampleWidget(conn)
    qtbot.addWidget(widget)

    # Test loading
    widget.load(1)
    assert (
        widget.name_edit.text() == conn.execute("SELECT name FROM samples WHERE id=1").fetchone()[0]
    )
