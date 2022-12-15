from cutevariant.core.engine import DuckDB
from cutevariant.core.engine.abstractdbengine import AbstractDB
from cutevariant.core.reader.fakereader import FakeReader

import pytest

ENGINES = [
    DuckDB(":memory:"),
]


@pytest.mark.parametrize("engine", ENGINES, ids=[str(i.__class__.__name__) for i in ENGINES])
def test_create_db(engine: AbstractDB):
    reader = FakeReader()
    print([i for i in reader.get_fields()])
    engine.create()
    engine.import_reader(reader)
    engine.get_fields()
