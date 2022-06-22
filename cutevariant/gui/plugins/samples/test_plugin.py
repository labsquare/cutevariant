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
    del sample["tags"]
    assert sample == {
        "id": 1,
        "name": "NORMAL",
        "family_id": "fam",
        "father_id": 0,
        "mother_id": 0,
        "sex": 0,
        "phenotype": 0,
        "classification": 0,
        "comment": "",
        "count_validation_negative_variant": 0,
        "count_validation_positive_variant": 0,
    }

    model.clear()
    assert model.rowCount() == 0
    qtmodeltester.check(model)
