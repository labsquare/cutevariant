
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


def test_create_command(conn):

    cmd = command.CreateCommand(conn) 
    cmd.source = "variants"
    cmd.target = "test" 

    selection = cmd.do()
    selection_id = selection["id"]
    
    
    source_q = conn.execute(f"SELECT COUNT(id) FROM variants").fetchone()[0]
    target_q= conn.execute(f"SELECT COUNT(id) FROM variants INNER JOIN selection_has_variant vs ON variants.id = vs.variant_id AND vs.selection_id = {selection_id}").fetchone()[0]

    assert source_q == target_q

def test_vql_command(conn):

    cmd = command.cmd_from_vql(conn, "SELECT chr, pos FROM variants")
    
    assert type(cmd) == command.SelectCommand
    assert cmd.columns == ["chr","pos"]
    assert cmd.source == "variants"

    cmd = command.cmd_from_vql(conn, "CREATE denovo FROM variants")
    
    assert type(cmd) == command.CreateCommand
    assert cmd.source == "variants"
    assert cmd.target == "denovo"





