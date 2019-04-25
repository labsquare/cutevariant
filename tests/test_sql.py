import pytest
import sqlite3
import os
from cutevariant.core import sql
from .utils import table_exists, table_count, table_drop


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
    expected = (("chr1", 10, "G", "A", 10, 100),)
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
        assert f == fields[index]


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
    sql.insert_selection(conn, name="selection_name", count=10)
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
    query = """SELECT variants.rowid,chr,pos,ref,alt FROM variants"""
    #    LEFT JOIN annotations
    #     ON annotations.variant_id = variants.rowid"""

    sql.create_selection_from_sql(conn, query, "selection_name", count=None, by="site")

    # Query the association table (variant_id, selection_id)
    data = conn.execute("SELECT * FROM selection_has_variant")
    expected = ((1, 1), (2, 1), (3, 1), (4, 1), (5, 1), (6, 1), (7, 1), (8, 1))
    record = tuple([tuple(i) for i in data])

    # Is the association table 'selection_has_variant' ok ?
    assert record == expected

    # Test ON CASCADE deletion
    cursor = conn.cursor()
    cursor.execute("DELETE FROM selections WHERE rowid = 1")

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


#     assert table_exists(conn, "selections"), "cannot create table selections"
#     sql.insert_selection(conn, name="variants", count=10)
#     assert table_count(conn, "selections") == 1, "cannot insert selection"


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
        assert tuple(record) == tuple(variants[i].values())
