
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


def test_select_command(conn):

    cmd = command.SelectCommand(conn)
    cmd.fields = ["chr","pos", "annotations.gene"]
    cmd.source = "variants"
    first_variant = next(cmd.do())
    assert "chr" in first_variant
    assert "pos" in first_variant
    assert "gene" in first_variant

def test_create_command(conn):

    cmd = command.CreateCommand(conn) 
    cmd.source = "variants"
    cmd.target = "test" 

    selection = cmd.do()
    assert "id" in selection 

    selection_id = selection["id"]
    source_q = conn.execute(f"SELECT COUNT(id) FROM variants").fetchone()[0]
    target_q= conn.execute(f"SELECT COUNT(id) FROM variants INNER JOIN selection_has_variant vs ON variants.id = vs.variant_id AND vs.selection_id = {selection_id}").fetchone()[0]


    assert source_q == target_q

def test_count_command(conn):
    cmd = command.CountCommand(conn)
    cmd.source = "variants"

    result = cmd.do()
    assert "count" in result 
    assert result["count"] == 11

def test_bed_command(conn):
    cmd = command.BedCommand(conn)
    cmd.source ="variants"
    cmd.target = "test"
    cmd.bedfile = "examples/test.bed"
    cmd.do()

def test_create_command_from_vql_objet(conn):

    cmd = command.create_command_from_vql_objet(conn, next(vql.execute_vql("SELECT chr, pos FROM variants")))
    assert type(cmd) == command.SelectCommand
    assert cmd.fields == ["chr","pos"]
    assert cmd.source == "variants"

    cmd = command.create_command_from_vql_objet(conn,  next(vql.execute_vql("CREATE denovo FROM variants")))
    assert type(cmd) == command.CreateCommand
    assert cmd.source == "variants"
    assert cmd.target == "denovo"

    cmd = command.create_command_from_vql_objet(conn,  next(vql.execute_vql("CREATE denovo = a + b ")))
    assert type(cmd) == command.SetCommand
    assert cmd.target == "denovo"
    assert cmd.first == "a"
    assert cmd.second == "b"

    cmd = command.create_command_from_vql_objet(conn,  next(vql.execute_vql("CREATE denovo FROM variants INTERSECT 'test.bed' ")))
    assert type(cmd) == command.BedCommand
    assert cmd.source == "variants"
    assert cmd.target == "denovo"
    assert cmd.bedfile == "test.bed"

def test_execute_vql(conn):


    # Select variant with ref = C
    result = command.execute_vql(conn, "CREATE setA FROM variants WHERE ref ='C'")
    assert "id" in result
    for variant in command.execute_vql(conn, "SELECT chr, pos, ref, alt FROM setA"):
        assert variant["ref"] == 'C'

    # Select variants with alt = A
    result = command.execute_vql(conn, "CREATE setB FROM variants WHERE alt ='A'")
    assert "id" in result
    for variant in command.execute_vql(conn, "SELECT chr, pos, ref, alt FROM setB"):
        assert variant["alt"] == 'A'

    #Create intersection 
    result = command.execute_vql(conn, "CREATE set_inter = setB & setA")
    assert "id" in result
    for variant in command.execute_vql(conn, "SELECT chr, pos, ref, alt FROM set_inter"):
        assert variant["alt"] == 'A' and variant["ref"] == 'C'

    # Create bedfile 
    BEDFILE = "examples/test.bed"
    result = command.execute_vql(conn, f"CREATE set_bed FROM variants INTERSECT '{BEDFILE}' ")
    assert "id" in result
    
    with open(BEDFILE) as file:
        reader = csv.reader(file, delimiter="\t")
        for variant in command.execute_vql(conn, "SELECT chr, pos, ref, alt FROM set_bed"):
            is_in = False
            file.seek(0)
            for line in reader:
                if len(line) == 3:
                    if str(line[0]) == str(variant["chr"]) and int(variant["pos"]) >= int(line[1]) and int(variant["pos"]) <= int(line[2]):
                        is_in = True
            assert is_in == True
        





