import pytest

from cutevariant.core import sql
from cutevariant.core.reader.bedreader import BedTool
from .utils import table_exists, table_count


@pytest.fixture
def conn():
    return sql.get_sql_connexion(":memory:")


fields = [
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
]

variants = [
    {"chr": "chr1", "pos": 10, "ref": "G", "alt": "A", "extra1": 10, "extra2": 100},
    {"chr": "chr1", "pos": 10, "ref": "C", "alt": "C", "extra1": 20, "extra2": 100},
    {"chr": "chr2", "pos": 20, "ref": "G", "alt": "G", "extra1": 30, "extra2": 100},
    {"chr": "chr3", "pos": 30, "ref": "A", "alt": "G", "extra1": 40, "extra2": 100.0},
    {"chr": "chr4", "pos": 40, "ref": "A", "alt": "G", "extra1": 50, "extra2": 100},
    {"chr": "chr1", "pos": 50, "ref": "C", "alt": "C", "extra1": 60, "extra2": 100},
    {"chr": "chr1", "pos": 60, "ref": "C", "alt": "T", "extra1": 70, "extra2": 100},
    {"chr": "chr1", "pos": 80, "ref": "C", "alt": "G", "extra1": 80, "extra2": 100},
]

duplicated_variants = [
    {"chr": "chr1", "pos": 10, "ref": "G", "alt": "A", "extra1": 10, "extra2": 100},
    {"chr": "chr1", "pos": 10, "ref": "G", "alt": "A", "extra1": 20, "extra2": 100},
]

variants_duplicated_annotations = [
    {"chr": "chr1", "pos": 10, "ref": "G", "alt": "A", "extra1": 10, "extra2": 100,
        "annotations": [{"gene": "gene1", "transcript": "transcript1"},]},
    {"chr": "chr1", "pos": 10, "ref": "C", "alt": "C", "extra1": 20, "extra2": 100,
        "annotations": [{"gene": "gene1", "transcript": "transcript1"},]},
]


def prepare_base(conn):

    sql.create_table_fields(conn)
    assert table_exists(conn, "fields"), "cannot create table fields"

    sql.create_table_samples(conn)
    assert table_exists(conn, "samples"), "cannot create table samples"

    sql.create_table_selections(conn)
    assert table_exists(conn, "selections"), "cannot create table selections"

    sql.insert_many_fields(conn, fields)
    assert table_count(conn, "fields") == len(fields), "cannot insert many fields"

    sql.create_table_variants(conn, sql.get_fields(conn))
    assert table_exists(conn, "variants"), "cannot create table variants"

    sql.insert_many_variants(conn, variants)


def test_duplicated_variants(conn):
    """Test the respect of the unicity constraint of the primary key

    => The second one must not be inserted

    .. warning:: Annotations attached to variants are still not tested here.
    """

    prepare_base(conn)

    # Delete all variants inserted by prepare_base()
    conn.execute("DELETE FROM variants")

    # Try to insert 2 duplicated variants
    sql.insert_many_variants(conn, duplicated_variants)

    # There must be only 1 variant (the first one)
    data = conn.execute("SELECT * FROM variants")
    expected = ((1, "chr1", 10, "G", "A", 10, 100),)
    record = tuple([tuple(i) for i in data])

    assert len(record) == 1

    assert record == expected


def test_duplicated_annotations(conn):
    """Test "annotations" table, by inserting 1 similar annotation to variants.

    => must not raise violation of unicity constraint exception

    .. warning:: This function doesn't test annotations with missing fields.
    (This has to be done when a file is imported because the annotationparser
    is called; which is not the case here).
    """

    # Create default annotations table
    # By default, these columns are created: "gene TEXT, transcript TEXT"
    sql.create_table_annotations(conn, [])

    prepare_base(conn)
    # Delete all variants inserted by prepare_base()
    conn.execute("DELETE FROM variants")

    # Try to insert 2 variants with the same annotations
    sql.insert_many_variants(conn, variants_duplicated_annotations)

    # There must be only 1 variant (the first one)
    data = conn.execute("SELECT * FROM annotations")
    record = tuple([tuple(i) for i in data])
    # Same annotation assigned to the 2 variants
    expected = tuple([(1, 'gene1', 'transcript1'), (2, 'gene1', 'transcript1')])

    assert record == expected


def test_fields(conn):

    prepare_base(conn)
    for index, f in enumerate(sql.get_fields(conn)):
        rowid = f.pop("id")
        assert f == fields[index]
        assert index+1 == rowid


def test_samples(conn):

    sql.create_table_samples(conn)
    assert table_exists(conn, "samples"), "cannot create table samples"

    samples = ["sacha", "boby", "guillaume"]

    for to_insert in samples:
        sql.insert_sample(conn, to_insert)

    assert [sample["name"] for sample in sql.get_samples(conn)] == samples


def test_simple_selections(conn):
    """Test creation and simple insertion of a line in "selections" table"""

    sql.create_table_selections(conn)
    sql.insert_selection(conn, "", name="selection_name", count=10)
    data = conn.execute("SELECT * FROM selections").fetchone()

    expected = (1, 'selection_name', 10, '')
    assert tuple(data) == expected


def test_selections(conn):
    """Test the creation of a full selection in "selection_has_variant"
    and "selections" tables; Test also the ON CASCADE deletion of rows in
    "selection_has_variant" when a selection is deleted.
    """

    prepare_base(conn)
    # Create a selection that contains all 8 variants in the DB
    # (no filter on this list, via annotation table because this table is not
    # initialized here)
    query = """SELECT variants.id,chr,pos,ref,alt FROM variants"""
    #    LEFT JOIN annotations
    #     ON annotations.variant_id = variants.rowid"""

    # Create a new selection (a second one, since there is a default one during DB creation)
    ret = sql.create_selection_from_sql(conn, query, "selection_name", count=None)
    assert ret == 2

    # Query the association table (variant_id, selection_id)
    data = conn.execute("SELECT * FROM selection_has_variant")
    expected = ((1, ret), (2, ret), (3, ret), (4, ret), (5, ret), (6, ret), (7, ret), (8, ret))
    record = tuple([tuple(i) for i in data])

    # Is the association table 'selection_has_variant' ok ?
    assert record == expected

    # Test ON CASCADE deletion
    cursor = conn.cursor()
    cursor.execute("DELETE FROM selections WHERE rowid = ?", str(ret))

    assert cursor.rowcount == 1

    # Now the table must be empty
    data = conn.execute("SELECT * FROM selection_has_variant")
    expected = tuple()
    record = tuple([tuple(i) for i in data])

    assert record == expected

    # Extra tests on transactions states
    assert conn.in_transaction == True
    conn.commit()
    assert conn.in_transaction == False


def test_selection_operation(conn):
    """test set operations on selections
    PS: try to handle precedence of operators"""
    prepare_base(conn)

    # Select all
    query = """SELECT variants.id,chr,pos,ref,alt FROM variants"""
    id_all = sql.create_selection_from_sql(conn, query, "all", count=None)

    # Select only ref = C (4 variants)
    query = """SELECT variants.id,chr,pos,ref,alt FROM variants WHERE ref='C'"""
    id_A = sql.create_selection_from_sql(conn, query, "setA", count=None,)

    # Select only alt = C (2 variants among setA)
    query = """SELECT variants.id,chr,pos,ref,alt FROM variants WHERE alt='C'"""
    id_B = sql.create_selection_from_sql(conn, query, "setB", count=None)

    assert all((id_all, id_A, id_B))

    selections = [selection["name"] for selection in sql.get_selections(conn)]

    assert "setA" in selections
    assert "setB" in selections

    sql.Selection.conn = conn

    All = sql.Selection.from_selection_id(id_all)
    A = sql.Selection.from_selection_id(id_A)
    B = sql.Selection.from_selection_id(id_B)

    # 8 - (4 & 2) = 8 - 2 = 6
    C = All - (B&A)
    # Query:
    # SELECT variant_id
    #    FROM selection_has_variant sv
    #     WHERE sv.selection_id = 2 EXCEPT SELECT * FROM (SELECT variant_id
    #    FROM selection_has_variant sv
    #     WHERE sv.selection_id = 4 INTERSECT SELECT variant_id
    #    FROM selection_has_variant sv
    #     WHERE sv.selection_id = 3)


    C.save("newset")

    print(A.sql_query)
    expected_number = 0
    for expected_number, variant in enumerate(conn.execute(A.sql_query), 1):
        print(dict(variant))

    assert expected_number == 4

    print(B.sql_query)
    expected_number = 0
    for expected_number, variant in enumerate(conn.execute(B.sql_query), 1):
        print(dict(variant))

    assert expected_number == 2

    print(C.sql_query)
    expected_number = 0
    for expected_number, variant in enumerate(conn.execute(C.sql_query), 1):
        print(dict(variant))

    assert expected_number == 6

    selections = [selection["name"] for selection in sql.get_selections(conn)]
    "newset" in selections

    # (8 - 2) & 4 = 2
    C = (All - B) & A
    # Query:
    # SELECT * FROM (SELECT variant_id
    #        FROM selection_has_variant sv
    #         WHERE sv.selection_id = 2 EXCEPT SELECT variant_id
    #        FROM selection_has_variant sv
    #         WHERE sv.selection_id = 4 INTERSECT SELECT variant_id
    #        FROM selection_has_variant sv
    #         WHERE sv.selection_id = 3)
    print(C.sql_query)
    expected_number = 0
    for expected_number, variant in enumerate(conn.execute(C.sql_query), 1):
        print(dict(variant))

    assert expected_number == 2


def test_selection_from_bedfile(conn):
    """Test the creation of a selection based on BED data

    .. note:: Please note that the bedreader **is not** tested here!
    """

    prepare_base(conn)

    larger_string = """
        chr1 1    10   feature1  0 +
        chr1 50   60   feature2  0 -
        chr1 51 59 another_feature 0 +
    """
    # 1: chr1, pos 1 to 10 => 2 variants
    # 2: chr1, pos 50 to 60 => 2 variants
    # 3: chr1, pos 51 to 59 => 0 variants

    bedtool = BedTool(larger_string)

    # Create a new selection (a second one, since there is a default one during DB creation)
    ret = sql.create_selection_from_bed(conn,"variants", "bedname", bedtool)
    

    # Test last id of the selection
    assert ret == 2

    # Query the association table (variant_id, selection_id)
    data = conn.execute("SELECT * FROM selection_has_variant WHERE selection_id = ?", (ret,))
    # 4 variants (see above)
    expected = ((1, ret), (2, ret), (6, ret), (7, ret))
    record = tuple([tuple(i) for i in data])

    # Is the association table 'selection_has_variant' ok ?
    assert record == expected

    bed_selection  = [s for s in sql.get_selections(conn) if s["name"] == "bedname"][0]
    assert bed_selection["name"] == "bedname"
    assert bed_selection["count"] == 4 


def test_selection_from_bedfile_and_subselection(conn):
    """Test the creation of a selection based on BED data

    .. note:: Please note that the bedreader **is not** tested here!
    """

    prepare_base(conn)


    larger_string = """
        chr1 1    10   feature1  0 +
        chr1 50   60   feature2  0 -
        chr1 51 59 another_feature 0 +
    """
    # 1: chr1, pos 1 to 10 => 2 variants
    # 2: chr1, pos 50 to 60 => 2 variants
    # 3: chr1, pos 51 to 59 => 0 variants

    bedtool = BedTool(larger_string)
 
    # Create now a sub selection 

    query = """SELECT variants.id,chr,pos,ref,alt FROM variants WHERE ref='C'"""
    set_A_id = sql.create_selection_from_sql(conn, query, "setA", count=None)

    assert "setA" in list(s["name"] for s in sql.get_selections(conn))

    # 1: chr1, pos 1 to 10 => 1 variants
    # 2: chr1, pos 50 to 60 => 2 variants
    # 3: chr1, pos 51 to 59 => 2 variants

    ret = sql.create_selection_from_bed(conn,"setA", "sub_bedname", bedtool)

    data = conn.execute("SELECT * FROM selection_has_variant WHERE selection_id = ?", (ret,))
    expected = ((2, ret), (6, ret), (7, ret))
    record = tuple([tuple(i) for i in data])
    assert record == expected
    
    
# def test_selection_operation(conn):

#     #  Prepare base
#     prepare_base(conn)
#     cursor = conn.cursor()

#     all_selection = cursor.execute("SELECT * FROM selections").fetchone()

#     print("all", all_selection)
#     assert all_selection[0] == "all"
#     assert all_selection[1] == len(variants)

#     #  Create a selection from sql
#     query = "SELECT chr, pos FROM variants where alt = 'A' "
#     sql.create_selection_from_sql(conn, "test", query)

#     # check if selection has been created
#     assert "test" in [record["name"] for record in sql.get_selections(conn)]

#     #  Check if selection of variants returns same data than selection query
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
    prepare_base(conn)

    for i, record in enumerate(conn.execute("SELECT * FROM variants")):
        record = list(record) # omit id
        assert tuple(record[1:]) == tuple(variants[i].values())
