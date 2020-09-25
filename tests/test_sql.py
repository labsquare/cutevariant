import pytest

from cutevariant.core import sql
from cutevariant.core.reader.bedreader import BedTool
from .utils import table_exists, table_count


FIELDS = [
    {
        "name": "chr",
        "category": "variants",
        "type": "text",
        "description": "chromosome",
    },
    {"name": "pos", "category": "variants", "type": "int", "description": "position"},
    {"name": "ref", "category": "variants", "type": "text", "description": "reference"},
    {
        "name": "alt",
        "category": "variants",
        "type": "text",
        "description": "alternative",
    },
    {
        "name": "extra1",
        "category": "variants",
        "type": "float",
        "description": "annotation 1",
    },
    {
        "name": "extra2",
        "category": "variants",
        "type": "int",
        "description": "annotation 2",
    },
    {
        "name": "gene",
        "category": "annotations",
        "type": "str",
        "description": "gene name",
    },
    {
        "name": "transcript",
        "category": "annotations",
        "type": "str",
        "description": "transcript name",
    },
    {
        "name": "gt",
        "category": "samples",
        "type": "int",
        "description": "sample genotype",
    },
    {"name": "dp", "category": "samples", "type": "int", "description": "sample dp"},
]

SAMPLES = ["sacha", "boby"]

VARIANTS = [
    {
        "chr": "chr1",
        "pos": 10,
        "ref": "G",
        "alt": "A",
        "extra1": 10,
        "extra2": 100,
        "annotations": [
            {"gene": "gene1", "transcript": "transcript1"},
            {"gene": "gene1", "transcript": "transcript2"},
        ],
        "samples": [
            {"name": "sacha", "gt": 1, "dp": 70},
            {"name": "boby", "gt": 1, "dp": 10},
        ],
    },
    {
        "chr": "chr1", "pos": 50, "ref": "C", "alt": "C", "extra1": 20, "extra2": 100,
        "annotations": [{"gene": "gene1", "transcript": "transcript1"},]
     },
    {
        "chr": "chr1",
        "pos": 45,
        "ref": "G",
        "alt": "A",
        "extra1": 20,
        "extra2": 100,
        "annotations": [{"gene": "gene2", "transcript": "transcript2"}],
        "samples": [
            {"name": "sacha", "gt": 0, "dp": 30},
            {"name": "boby", "gt": 0, "dp": 70},
        ],
    },
]


FILTERS = {
    "AND": [
        {"field": "chr", "operator": "=", "value": "chr1"},
        {
            "OR": [
                {"field": "gene", "operator": "=", "value": "gene1"},
                {"field": "pos", "operator": "=", "value": 10},
            ]
        },
    ]
}


@pytest.fixture
def conn():
    conn = sql.get_sql_connexion(":memory:")

    sql.create_project(conn, "test", "hg19")
    assert table_exists(conn, "projects"), "cannot create table projects"

    sql.create_table_fields(conn)
    assert table_exists(conn, "fields"), "cannot create table fields"

    sql.insert_many_fields(conn, FIELDS)
    assert table_count(conn, "fields") == len(FIELDS), "cannot insert many fields"

    sql.create_table_selections(conn)
    assert table_exists(conn, "selections"), "cannot create table selections"

    sql.create_table_annotations(conn, sql.get_field_by_category(conn, "annotations"))
    assert table_exists(conn, "annotations"), "cannot create table annotations"

    sql.create_table_samples(conn, sql.get_field_by_category(conn, "samples"))
    assert table_exists(conn, "samples"), "cannot create table samples"
    sql.insert_many_samples(conn, SAMPLES)

    sql.create_table_variants(conn, sql.get_field_by_category(conn, "variants"))
    assert table_exists(conn, "variants"), "cannot create table variants"
    sql.insert_many_variants(conn, VARIANTS)

    sql.create_table_sets(conn)
    assert table_exists(conn, "sets"), "cannot create table sets"

    return conn


def test_create_connexion(conn):
    assert conn is not None


def test_get_columns(conn):
    sql.get_columns(conn, "variants") == [
        i["name"] for i in FIELDS if i["category"] == "variants"
    ]
    raise NotImplementedError


def test_get_annotations(conn):
    for id, variant in enumerate(VARIANTS):
        read_tx = list(sql.get_annotations(conn, id + 1))[0]
        del read_tx["variant_id"]
        expected_tx = VARIANTS[id]["annotations"][0]
        assert read_tx == expected_tx
    # TODO: CHECK

def test_get_sample_annotations(conn):
    raise NotImplementedError


def test_get_fields(conn):
    # Test if fields returns
    for index, f in enumerate(sql.get_fields(conn)):
        rowid = f.pop("id")
        assert f == FIELDS[index]
        assert index + 1 == rowid


def test_get_samples(conn):
    assert [sample["name"] for sample in sql.get_samples(conn)] == SAMPLES
    first_sample = list(sql.get_samples(conn))[0]

    # test default value
    assert first_sample["name"] == "sacha"
    assert first_sample["fam"] == "fam"
    assert first_sample["father_id"] == 0
    assert first_sample["mother_id"] == 0
    assert first_sample["sex"] == 0
    assert first_sample["phenotype"] == 0


def test_update_samples(conn):
    previous_sample = list(sql.get_samples(conn))[0]

    assert previous_sample["name"] == "sacha"
    assert previous_sample["id"] == 1
    # Update with info
    previous_sample["name"] = "maco"
    previous_sample["fam"] = "fam2"
    previous_sample["father_id"] = 1
    previous_sample["mother_id"] = 1
    previous_sample["sex"] = 2
    previous_sample["phenotype"] = 2

    sql.update_sample(conn, previous_sample)

    edit_sample = list(sql.get_samples(conn))[0]

    assert edit_sample["name"] == "maco"
    assert edit_sample["fam"] == "fam2"
    assert edit_sample["father_id"] == 1
    assert edit_sample["mother_id"] == 1
    assert edit_sample["sex"] == 2
    assert edit_sample["phenotype"] == 2


def test_update_variant(conn):
    """exception si pas id, ajout comment"""

    updated = {"id": 1, "ref": "A", "chr": "chrX"}
    sql.update_variant(conn, updated)

    inserted = sql.get_one_variant(conn, 1)

    assert inserted["ref"] == updated["ref"]
    assert inserted["chr"] == updated["chr"]


def test_insert_set_from_file(conn):
    """Test the insertion of gene names from file into the database

    TODO: simulate much more problematic data from biologists please!
    """
    filename = tempfile.mkstemp()[1]
    data = ["GJB2", "CFTR", "KRAS", "BRCA1"]

    # Simulate a file with a list of genes (1 per line)
    with open(filename, "w") as fp:
        fp.write("\n".join(data))

    sql.insert_set_from_file(conn, "test", filename)

    # TODO: for now the one to many relation is not implemented
    # All records have the name of the set... awesome
    for record in conn.execute("SELECT * FROM sets").fetchall():
        record = dict(record)
        assert record["name"] == "test"
        assert record["value"] in data


def test_selections(conn):
    """Test the creation of a full selection in "selection_has_variant"
    and "selections" tables; Test also the ON CASCADE deletion of rows in
    "selection_has_variant" when a selection is deleted.
    """

    # Create a selection that contains all 8 variants in the DB
    # (no filter on this list, via annotation table because this table is not
    # initialized here)
    query = """SELECT variants.id,chr,pos,ref,alt FROM variants"""
    #    LEFT JOIN annotations
    #     ON annotations.variant_id = variants.rowid"""

    # Create a new selection (a second one, since there is a default one during DB creation)
    # ret = sql.create_selection_from_sql(conn, query, "selection_name", count=None)
    # assert ret == 2

    # # Query the association table (variant_id, selection_id)
    # data = conn.execute("SELECT * FROM selection_has_variant")
    # expected = ((1, ret), (2, ret), (3, ret), (4, ret), (5, ret), (6, ret), (7, ret), (8, ret))
    # record = tuple([tuple(i) for i in data])

    # # Is the association table 'selection_has_variant' ok ?
    # assert record == expected

    # # Test ON CASCADE deletion
    # cursor = conn.cursor()
    # cursor.execute("DELETE FROM selections WHERE rowid = ?", str(ret))

    # assert cursor.rowcount == 1

    # # Now the table must be empty
    # data = conn.execute("SELECT * FROM selection_has_variant")
    # expected = tuple()
    # record = tuple([tuple(i) for i in data])

    # assert record == expected

    # # Extra tests on transactions states
    # assert conn.in_transaction == True
    # conn.commit()
    # assert conn.in_transaction == False
    raise NotImplementedError


def test_selection_operation(conn):
    """test set operations on selections
    PS: try to handle precedence of operators"""

    # Select all
    query = """SELECT variants.id,chr,pos,ref,alt FROM variants"""
    id_all = sql.create_selection_from_sql(conn, query, "all", count=None)

    # Select only ref = C (4 variants)
    query = """SELECT variants.id,chr,pos,ref,alt FROM variants WHERE ref='C'"""
    id_A = sql.create_selection_from_sql(conn, query, "setA", count=None,)

    # Select only alt = C (2 variants among setA)
    query = """SELECT variants.id,chr,pos,ref,alt FROM variants WHERE alt='C'"""
    id_B = sql.create_selection_from_sql(conn, query, "setB", count=None)
    raise NotImplementedError

    # assert all((id_all, id_A, id_B))

    # selections = [selection["name"] for selection in sql.get_selections(conn)]

    # assert "setA" in selections
    # assert "setB" in selections

    # sql.Selection.conn = conn

    # All = sql.Selection.from_selection_id(id_all)
    # A = sql.Selection.from_selection_id(id_A)
    # B = sql.Selection.from_selection_id(id_B)

    # # 8 - (4 & 2) = 8 - 2 = 6
    # C = All - (B&A)
    # # Query:
    # # SELECT variant_id
    # #    FROM selection_has_variant sv
    # #     WHERE sv.selection_id = 2 EXCEPT SELECT * FROM (SELECT variant_id
    # #    FROM selection_has_variant sv
    # #     WHERE sv.selection_id = 4 INTERSECT SELECT variant_id
    # #    FROM selection_has_variant sv
    # #     WHERE sv.selection_id = 3)

    # C.save("newset")

    # print(A.sql_query)
    # expected_number = 0
    # for expected_number, variant in enumerate(conn.execute(A.sql_query), 1):
    #     print(dict(variant))

    # assert expected_number == 4

    # print(B.sql_query)
    # expected_number = 0
    # for expected_number, variant in enumerate(conn.execute(B.sql_query), 1):
    #     print(dict(variant))

    # assert expected_number == 2

    # print(C.sql_query)
    # expected_number = 0
    # for expected_number, variant in enumerate(conn.execute(C.sql_query), 1):
    #     print(dict(variant))

    # assert expected_number == 6

    # selections = [selection["name"] for selection in sql.get_selections(conn)]
    # "newset" in selections

    # # (8 - 2) & 4 = 2
    # C = (All - B) & A
    # # Query:
    # # SELECT * FROM (SELECT variant_id
    # #        FROM selection_has_variant sv
    # #         WHERE sv.selection_id = 2 EXCEPT SELECT variant_id
    # #        FROM selection_has_variant sv
    # #         WHERE sv.selection_id = 4 INTERSECT SELECT variant_id
    # #        FROM selection_has_variant sv
    # #         WHERE sv.selection_id = 3)
    # print(C.sql_query)
    # expected_number = 0
    # for expected_number, variant in enumerate(conn.execute(C.sql_query), 1):
    #     print(dict(variant))

    # assert expected_number == 2


# ============ TEST VARIANTS QUERY


def test_select_variant_items(conn):
    args = {}
    # assert len(list(sql.SelectVariant(conn, **args).items())) == len(VARIANTS)

    # args = {"filters": filters}
    # assert len(list(sql.get_variants(conn, **args))) == 1

    # TODO more test
    raise NotImplementedError


def test_selection_from_bedfile(conn):
    """Test the creation of a selection based on BED data

    .. note:: Please note that the bedreader **is not** tested here!
    """

    larger_string = """
        chr1 1    10   feature1  0 +
        chr1 50   60   feature2  0 -
        chr1 51 59 another_feature 0 +
    """
    # According to VARIANTS global variable with 3 variants (pos 10, 50 and 45)
    # 1: chr1, pos 1 to 10 => 1 variant concerned (pos 10)
    # 2: chr1, pos 50 to 60 => 1 variant concerned (pos 50)
    # 3: chr1, pos 51 to 59 => 0 variants

    bedtool = BedTool(larger_string)

    # Create a new selection (a second one, since there is a default one during DB creation)
    selection_name = "bedname"
    ret = sql.create_selection_from_bed(conn,"variants", selection_name, bedtool)

    # Test last id of the selection
    assert ret == 2

    # Query the association table (variant_id, selection_id)
    data = conn.execute("SELECT * FROM selection_has_variant WHERE selection_id = ?", (ret,))
    # 2 variants (see above)
    # format: [(id variant, id selection),]
    expected = ((1, ret), (2, ret))
    record = tuple([tuple(i) for i in data])

    # Is the association table 'selection_has_variant' ok ?
    print("record:", record)
    assert record == expected

    bed_selection = [s for s in sql.get_selections(conn) if s["name"] == selection_name][0]
    print("selection content", bed_selection)
    assert bed_selection["name"] == selection_name
    assert bed_selection["count"] == 2  # 2 variants retrieved


def test_selection_from_bedfile_and_subselection(conn):
    """Test the creation of a selection based on BED data

    .. note:: Please note that the bedreader **is not** tested here!
    """
    raise NotImplementedError
    larger_string = """
        chr1 1    10   feature1  0 +
        chr1 50   60   feature2  0 -
        chr1 51 59 another_feature 0 +
    """
    # 1: chr1, pos 1 to 10 => 2 variants
    # 2: chr1, pos 50 to 60 => 2 variants
    # 3: chr1, pos 51 to 59 => 0 variants


# bedtool = BedTool(larger_string)

# Create now a sub selection

# query = """SELECT variants.id,chr,pos,ref,alt FROM variants WHERE ref='C'"""
# set_A_id = sql.create_selection_from_sql(conn, query, "setA", count=None)

# assert "setA" in list(s["name"] for s in sql.get_selections(conn))

# # 1: chr1, pos 1 to 10 => 1 variants
# # 2: chr1, pos 50 to 60 => 2 variants
# # 3: chr1, pos 51 to 59 => 2 variants

# ret = sql.create_selection_from_bed(conn,"setA", "sub_bedname", bedtool)

# data = conn.execute("SELECT * FROM selection_has_variant WHERE selection_id = ?", (ret,))
# expected = ((2, ret), (6, ret), (7, ret))
# record = tuple([tuple(i) for i in data])
# assert record == expected


def test_selection_operation(conn):
    raise NotImplementedError

#     # Prepare base
#     prepare_base(conn)
#     cursor = conn.cursor()

#     all_selection = cursor.execute("SELECT * FROM selections").fetchone()

#     print("all", all_selection)
#     assert all_selection[0] == "all"
#     assert all_selection[1] == len(variants)

#     # Create a selection from sql
#     query = "SELECT chr, pos FROM variants where alt = 'A' "
#     sql.create_selection_from_sql(conn, "test", query)

#     # check if selection has been created
#     assert "test" in [record["name"] for record in sql.get_selections(conn)]

#     # Check if selection of variants returns same data than selection query
#     selection_id = 2
#     insert_data = cursor.execute(query).fetchall()

#     read_data = cursor.execute(
#         f"""
#         SELECT variants.chr, variants.pos FROM variants
#         INNER JOIN selection_has_variant sv ON variants.rowid = sv.variant_id AND sv.selection_id = {selection_id}
#         """
#     ).fetchall()

#     # set because, it can contains duplicate variants
#     assert set(read_data) == set(insert_data)

#     # TEST Unions
#     query1 = "SELECT chr, pos FROM variants where alt = 'G' "
#     query2 = "SELECT chr, pos FROM variants where alt = 'T' "

#     union_query = sql.union_variants(query1, query2)
#     print(union_query)
#     sql.create_selection_from_sql(conn, "union_GT", union_query)
#     record = cursor.execute(
#         f"SELECT rowid, name FROM selections WHERE name = 'union_GT'"
#     ).fetchone()
#     selection_id = record[0]
#     selection_name = record[1]
#     assert selection_id == 3  # test if selection id equal 2 ( the first is "variants")
#     assert selection_name == "union_GT"

#     # Select statement from union_GT selection must contains only variant.alt G or T
#     records = cursor.execute(
#         f"""
#         SELECT variants.chr, variants.pos, variants.ref, variants.alt FROM variants
#         INNER JOIN selection_has_variant sv ON variants.rowid = sv.variant_id AND sv.selection_id = {selection_id}
#         """
#     ).fetchall()

#     for record in records:
#         assert record[3] in ("G", "T")

#     # Todo : test intersect and expect


def test_variants(conn):
    """Test that we have all inserted variants in the DB"""

    for i, record in enumerate(conn.execute("SELECT * FROM variants")):
        record = list(record)[1:]  # omit id
        expected_variant = VARIANTS[i]

        # Check only variants, not annotations or samples
        for not_wanted_key in ("annotations", "samples"):
            if not_wanted_key in expected_variant:
                del expected_variant[not_wanted_key]

        assert tuple(record) == tuple(expected_variant.values())
