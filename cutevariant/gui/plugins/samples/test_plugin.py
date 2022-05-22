import pytest

from .widgets import SampleModel
import pytestqt
from tests import utils


def test_model(qtmodeltester):
    conn = utils.create_conn()
    model = SampleModel(conn)
    model._selected_samples = ["TUMOR", "NORMAL"]

    model.load()
    assert model.rowCount() == 2

    # Check samples
    sample = model.get_sample(0)
    assert sample == {
        "id": 1,
        "name": "NORMAL",
        "family_id": "fam",
        "father_id": 0,
        "mother_id": 0,
        "sex": 0,
        "phenotype": 0,
        "classification": 0,
        "tags": "",
        "comment": "",
    }

    model.clear()
    assert model.rowCount() == 0
    qtmodeltester.check(model)
