from cutevariant.core.quicksearch import quicksearch
from cutevariant.config import Config
import pytest

config = Config("variables")
gene_col = config.get("gene_field", "ann.gene")
EXAMPLE_QUERIES = [
    ("CFTR", {"$and": [{gene_col: "CFTR"}]}),
    ("ref='A'", {"$and": [{"ref": {"$eq": "A"}}]}),
    (
        "chr7:117120017-117308718",
        {
            "$and": [
                {"chr": "chr7"},
                {"pos": {"$gte": 117120017}},
                {"pos": {"$lte": 117308718}},
            ]
        },
    ),
    ("", dict()),
    ("chr7:42", {"$and": [{"chr": "chr7"}, {"pos": {"$eq": 42}}]}),
]


@pytest.mark.parametrize("item", EXAMPLE_QUERIES, ids=[ex[0] for ex in EXAMPLE_QUERIES])
def test_quicksearch(item):
    user_query, expected_filter = item
    assert expected_filter == quicksearch(user_query)
