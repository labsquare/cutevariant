from cutevariant.core import command, sql, vql
from cutevariant.core.reader import VcfReader
from cutevariant.core.importer import import_reader
import pytest
import csv


@pytest.fixture
def conn():
    conn = sql.get_sql_connexion(":memory:")
    import_reader(conn, VcfReader(open("examples/test.snpeff.vcf"), "snpeff"))
    return conn


def test_select_cmd(conn):

    variant = next(
        command.select_cmd(conn, fields=["chr", "pos", "gene"], source="variants")
    )

    assert "chr" in variant
    assert "pos" in variant
    assert "gene" in variant


def test_select_cmd_with_set(conn):
    """Test the select query of gene sets"""
    # Import fake words (gene) as a new set called "test"
    geneSets = ["CHID1", "AP2A2"]
    for gene in geneSets:
        conn.execute(f"INSERT INTO sets (name,value) VALUES ('test', '{gene}') ")

    filters = {"AND": [{"field": "gene", "operator": "IN", "value": ("SET", "test")}]}

    for variant in command.select_cmd(
        conn, fields=["chr", "ref", "alt", "gene"], source="variants", filters=filters
    ):
        assert variant["gene"] in geneSets

    # filters  = {"AND": {"field":"gene", }}


def test_create_cmd(conn):
    """Test creation of a selection table based on default 'variants' table"""
    result = command.create_cmd(conn, source="variants", target="test")
    print("create_cmd result:", result)
    assert "id" in result

    # Get the id of the created selection
    selection_id = result["id"]
    # The count of variants in the selection must be the same as in variants table
    source_q = conn.execute(f"SELECT COUNT(id) FROM variants").fetchone()[0]
    target_q = conn.execute(
        f"SELECT COUNT(id) FROM variants INNER JOIN selection_has_variant vs ON variants.id = vs.variant_id AND vs.selection_id = {selection_id}"
    ).fetchone()[0]
    assert source_q == target_q


def test_count_cmd(conn):
    """Test variants counting in variants table"""
    result = command.count_cmd(conn, source="variants")
    assert "count" in result
    assert result["count"] == 11


def test_drop_cmd(conn):
    """Test drop command on selections table"""

    # Create a selection named "subset"
    conn.execute("INSERT INTO selections (name) VALUES ('subset')")
    assert "subset" in [
        i["name"] for i in conn.execute("SELECT name FROM selections").fetchall()
    ]
    ret = command.drop_cmd(conn, feature="selections", name="subset")
    assert "subset" not in [
        i["name"] for i in conn.execute("SELECT name FROM selections").fetchall()
    ]
    assert ret["success"]


def test_bed_cmd(conn):
    """Test bed file insertion as selection"""
    ret = command.bed_cmd(
        conn, source="variants", target="test", path="examples/test.bed"
    )
    # Number of selections = id of last selection
    selection_number = conn.execute("SELECT COUNT(*) from selections").fetchone()[0]
    assert ret["id"] == selection_number

    # Test data in association table
    variants_in_selection = conn.execute(
        "SELECT COUNT(*) from selection_has_variant"
    ).fetchone()[0]
    # 3 variants are concerned by the bed intervals
    expected = 3
    assert variants_in_selection == expected


def test_set_cmd(conn):
    """Test set operation between 2 selections"""
    command.create_cmd(conn, source="variants", target="A")
    command.create_cmd(conn, source="variants", target="B")
    selection_C = command.set_cmd(conn, target="C", first="A", second="B", operator="-")
    # Substraction of A (11 variants) - B (11 variants) results in 0 variant
    # Since create_selection_from_sql does a rollback, C selection is not present
    # return is empty
    assert selection_C == dict()
    ret = list(command.select_cmd(conn, fields=["chr", "pos", "gene"], source="C"))
    expected = 0
    assert len(ret) == expected

    # selection 1: variants
    # 2: A
    # 3: B
    # => C is not created
    selection_number = conn.execute("SELECT COUNT(*) from selections").fetchone()[0]
    assert selection_number == 3

    # C = A | B
    selection_C = command.set_cmd(conn, target="C", first="A", second="B", operator="+")
    selection_C_id = selection_C["id"]
    print(selection_C_id)
    variants_in_selection = conn.execute(
        f"SELECT DISTINCT COUNT(*) from selection_has_variant WHERE selection_id = {selection_C_id}"
    ).fetchone()[0]

    expected = 11
    assert variants_in_selection == expected


def test_import_cmd(conn):
    """Test import word set from file (import_cmd is for word sets only FOR NOW)

    Import from a kindly external file with 2 genes.
    """
    # Test import of word set
    test_file = "examples/gene.txt"
    wordset_name = "boby"

    excepted_word = []
    with open(test_file, "r") as file:
        for word in file:
            excepted_word.append(word.strip())

    command.import_cmd(conn, "sets", wordset_name, test_file)

    for record in conn.execute("SELECT * FROM sets"):
        item = dict(record)
        assert item["name"] == wordset_name


def test_create_command_from_obj(conn):
    """Test create_command_from_obj

    - Test from VQL Query
    - Test from VQL Object
    """
    ## From VQL Query ##########################################################
    cmd = command.create_command_from_obj(
        conn, next(vql.execute_vql("CREATE denovo FROM variants"))
    )
    expected_kwargs = {
        "cmd": "create_cmd",
        "source": "variants",
        "filters": {},
        "target": "denovo",
    }
    print(cmd.keywords)
    assert cmd.keywords == expected_kwargs

    cmd = command.create_command_from_obj(
        conn, next(vql.execute_vql("CREATE denovo = a + b "))
    )
    print(cmd.keywords)
    expected_kwargs = {
        "cmd": "set_cmd",
        "target": "denovo",
        "first": "a",
        "operator": "+",
        "second": "b",
    }
    assert cmd.keywords == expected_kwargs

    cmd = command.create_command_from_obj(
        conn, next(vql.execute_vql("CREATE denovo FROM variants INTERSECT 'test.bed' "))
    )
    # Keywords of partial function
    expected_kwargs = {
        "cmd": "bed_cmd",
        "target": "denovo",
        "source": "variants",
        "path": "test.bed",
    }
    assert cmd.keywords == expected_kwargs

    ## From VQL objects ########################################################
    expected_kwargs = {
        "cmd": "create_cmd",
        "fields": ["chr", "pos"],
        "target": "test",
        "source": "variants",
        "filters": {},
    }
    partial_fct = command.create_command_from_obj(
        conn,
        expected_kwargs,
    )
    print(partial_fct.keywords)
    assert partial_fct.keywords == expected_kwargs

    expected_kwargs = {
        "cmd": "select_cmd",
        "fields": ["chr", "pos"],
        "source": "variants",
        "filters": {},
    }
    partial_fct = command.create_command_from_obj(
        conn,
        expected_kwargs,
    )
    print(partial_fct.keywords)
    assert partial_fct.keywords == expected_kwargs


def test_execute(conn):
    """Test the wrapper of create_command_from_obj()

    Translate VQL string to SQL wrapped query
    """

    # Select variant with ref = C (4 variants)
    result = command.execute(conn, "CREATE setA FROM variants WHERE ref='C'")

    assert "id" in result

    for variant in command.execute(conn, "SELECT chr, pos, ref, alt FROM setA"):
        assert variant["ref"] == "C"

    # Select variants with alt = A (7 variants)
    result = command.execute(conn, "CREATE setB FROM variants WHERE alt ='A'")
    assert "id" in result
    for variant in command.execute(conn, "SELECT chr, pos, ref, alt FROM setB"):
        assert variant["alt"] == "A"

    # Create intersection (3 in common)
    result = command.execute(conn, "CREATE set_inter = setB & setA")
    assert "id" in result
    for found, variant in enumerate(
        command.execute(conn, "SELECT chr, pos, ref, alt FROM set_inter"), 1
    ):
        assert variant["alt"] == "A" and variant["ref"] == "C"

    print("Expected number of variants:", found)
    assert found == 3

    #  Create bedfile
    bed_file = "examples/test.bed"
    result = command.execute(
        conn, f"CREATE set_bed FROM variants INTERSECT '{bed_file}' "
    )
    assert "id" in result

    # Check that variants in intervals were added in DB
    with open(bed_file) as file:
        reader = csv.reader(file, delimiter="\t")
        for variant in command.execute(conn, "SELECT chr, pos, ref, alt FROM set_bed"):
            is_in = False
            file.seek(0)
            for line in reader:
                if len(line) == 3:
                    if (
                        str(line[0]) == str(variant["chr"])
                        and int(line[1]) <= int(variant["pos"]) <= int(line[2])
                    ):
                        is_in = True
            assert is_in
