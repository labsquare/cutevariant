import pytest

from .widgets import SampleModel
import pytestqt
from tests import utils


def test_model(qtmodeltester):
    conn = utils.create_conn()
    model = SampleModel(conn)

    model.load()
    assert model.rowCount() == 2
    model.clear()
    assert model.rowCount() == 0
    qtmodeltester.check(model)
