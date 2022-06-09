import os
import pytest

from cutevariant.core.report import SampleReport

TEMPLATES = ["examples/sample_report_template01.docx"]
OUTPUTS = ["examples/sample_report01.docx"]

@pytest.mark.usefixtures("conn")
def test_sample_report(conn):
    """
    Test simple report creation
    """
    r = SampleReport(conn, 1)

    r._set_data()
    data = r._get_data()
    assert data["sample"]["name"] == "sacha"

    for i in range(len(TEMPLATES)):

        if os.path.exists(OUTPUTS[i]):
            os.remove(OUTPUTS[i])

        r.create(TEMPLATES[i], OUTPUTS[i])
        assert os.path.exists(OUTPUTS[i])