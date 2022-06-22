from cutevariant.gui.widgets import SampleWidget
from cutevariant.core import sql
from tests import utils


def test_widget(qtbot):
    conn = utils.create_conn()

    widget = SampleWidget(conn)
    qtbot.addWidget(widget)

    # Test loading
    widget.load(1)
