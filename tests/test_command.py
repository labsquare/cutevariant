
from cutevariant.core import command , sql, vql
from cutevariant.core.reader import VcfReader
from cutevariant.core.importer import import_reader
import pytest
import csv

@pytest.fixture
def conn():
    conn = sql.get_sql_connexion(":memory:")
    import_reader(conn, VcfReader(open("examples/test.snpeff.vcf"),"snpeff"))
    return conn


def test_select_cmd(conn):

    variant = next(command.select_cmd(conn, fields = ["chr","pos","gene"], source="variants"))

    assert "chr" in variant
    assert "pos" in variant
    assert "gene" in variant

def test_create_cmd(conn):

    result = command.create_cmd(conn, source = "variants", target="test")

    assert "id" in result 

    selection_id = result["id"]
    source_q = conn.execute(f"SELECT COUNT(id) FROM variants").fetchone()[0]
    target_q= conn.execute(f"SELECT COUNT(id) FROM variants INNER JOIN selection_has_variant vs ON variants.id = vs.variant_id AND vs.selection_id = {selection_id}").fetchone()[0]


    assert source_q == target_q

def test_count_cmd(conn):
    result = command.count_cmd(conn, source="variants")
    assert "count" in result 
    assert result["count"] == 11


def test_drop_cmd(conn):

    conn.execute("INSERT INTO selections (name) VALUES ('subset')")
    assert "subset" in [i["name"] for i in conn.execute("SELECT name FROM selections").fetchall()]
    command.drop_cmd(conn, source="subset")
    assert "subset" not in [i["name"] for i in conn.execute("SELECT name FROM selections").fetchall()]


def test_bed_cmd(conn):
    command.bed_cmd(conn, source="variants", target="test", path="examples/test.bed")


def test_set_cmd(conn):
    command.create_cmd(conn, source = "variants", target="A")
    command.create_cmd(conn, source = "variants", target="B")
    command.set_cmd(conn, target="C", first="A", second="B", operator="+")



    # assert type(cmd) == command.SelectCommand
    # assert cmd.fields == ["chr","pos"]
    # assert cmd.source == "variants"

    # cmd = command.create_command_from_vql_objet(conn,  next(vql.execute_vql("CREATE denovo FROM variants")))
    # assert type(cmd) == command.CreateCommand
    # assert cmd.source == "variants"
    # assert cmd.target == "denovo"

    # cmd = command.create_command_from_vql_objet(conn,  next(vql.execute_vql("CREATE denovo = a + b ")))
    # assert type(cmd) == command.SetCommand
    # assert cmd.target == "denovo"
    # assert cmd.first == "a"
    # assert cmd.second == "b"

    # cmd = command.create_command_from_vql_objet(conn,  next(vql.execute_vql("CREATE denovo FROM variants INTERSECT 'test.bed' ")))
    # assert type(cmd) == command.BedCommand
    # assert cmd.source == "variants"
    # assert cmd.target == "denovo"
    # assert cmd.bedfile == "test.bed"


def test_create_command_from_obj(conn):
    import inspect 
    partial_fct = command.create_command_from_obj(conn, {"cmd":"create_cmd", "fields": ["chr","pos"], "target":"test", "source":"variants", "filters": {}})
    assert partial_fct.func == command.create_cmd

    partial_fct = command.create_command_from_obj(conn, {"cmd":"select_cmd", "fields": ["chr","pos"], "source":"variants", "filters": {}})
    assert partial_fct.func == command.select_cmd

    # etc ... 

def test_execute(conn):


    # Select variant with ref = C
    result = command.execute(conn, "CREATE setA FROM variants WHERE ref='C'")

    assert "id" in result 
    
    for variant in command.execute(conn, "SELECT chr, pos, ref, alt FROM setA"):
        assert variant["ref"] == 'C'

    # Select variants with alt = A
    result = command.execute(conn, "CREATE setB FROM variants WHERE alt ='A'")
    assert "id" in result
    for variant in command.execute(conn, "SELECT chr, pos, ref, alt FROM setB"):
        assert variant["alt"] == 'A'

    #Create intersection 
    result = command.execute(conn, "CREATE set_inter = setB & setA")
    assert "id" in result
    for variant in command.execute(conn, "SELECT chr, pos, ref, alt FROM set_inter"):
        assert variant["alt"] == 'A' and variant["ref"] == 'C'

    # Create bedfile 
    BEDFILE = "examples/test.bed"
    result = command.execute(conn, f"CREATE set_bed FROM variants INTERSECT '{BEDFILE}' ")
    assert "id" in result
    
    with open(BEDFILE) as file:
        reader = csv.reader(file, delimiter="\t")
        for variant in command.execute(conn, "SELECT chr, pos, ref, alt FROM set_bed"):
            is_in = False
            file.seek(0)
            for line in reader:
                if len(line) == 3:
                    if str(line[0]) == str(variant["chr"]) and int(variant["pos"]) >= int(line[1]) and int(variant["pos"]) <= int(line[2]):
                        is_in = True
            assert is_in == True
        





