import os
import pytest
import tempfile
from cutevariant.core.report import SampleReport

TEMPLATE = """
<!DOCTYPE html>
<head>
    <title>Document</title>
</head>
<body>
    {{sample.name}}
    
</body>
</html>
"""


@pytest.mark.usefixtures("conn")
def test_sample_report(conn):
    """
    Test simple report creation
    """

    # Create template
    with tempfile.NamedTemporaryFile(delete=False) as fp:
        fp.write(TEMPLATE.encode("utf-8"))

    report = SampleReport(conn, 1)
    data = report.get_data()
    assert data["sample"]["name"] == "sacha"
    report.set_template(fp.name)

    with tempfile.NamedTemporaryFile(delete=False) as output:
        report.create(output.name)

    assert os.path.getsize(output.name) > 0

    os.remove(fp.name)
    os.remove(output.name)
