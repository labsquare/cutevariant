import pytest

from cutevariant.gui.widgets.variant_widget import (
    EvaluationSectionWidget,
    VariantSectionWidget,
    AnnotationsSectionWidget,
    OccurenceModel,
    OccurrenceSectionWidget,
    HistorySectionWidget,
    VariantWidget
)

VARIANT = {
    "chr": "chr1",
    "pos": 10,
    "ref": "G",
    "alt": "A",
    "favorite": 0,
    "classification": 0,
    "tags": "",
    "comment": "",
    "dp": None,
    "extra1": 10,
    "extra2": 100,
    "qual": 15,
    "annotations": [
        {"gene": "gene1", "transcript": "transcript1"},
        {"gene": "gene1", "transcript": "transcript2"},
    ],
    "samples": [
        {"name": "sacha", "gt": 1, "dp": 70},
        {"name": "boby", "gt": 1, "dp": 10},
    ],
}

@pytest.mark.usefixtures("conn")
def test_evaluation_section_widget(conn, qtbot):
    """
    Test simple report creation
    """
    widget = EvaluationSectionWidget()
    qtbot.addWidget(widget)

    widget.set_variant(VARIANT)
    assert widget.get_variant() == {"favorite": 0, "classification": 0, "tags": "", "comment": ""}



