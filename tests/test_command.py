
from cutevariant.core import command , sql
from cutevariant.core.reader import VcfReader
from cutevariant.core.importer import import_reader
import pytest

@pytest.fixture
def conn():
    conn = sql.get_sql_connexion(":memory:")
    import_reader(conn, VcfReader(open("examples/test.snpeff.vcf"),"snpeff"))
    return conn


def test_select_command(conn):

    cmd = command.SelectCommand(conn)
    cmd.columns = ["chr","pos", "annotations.gene"]
    cmd.source = "variants"

    for variant in cmd.do():
        print(variant)





