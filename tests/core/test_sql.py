import sqlite3
import pytest
import tempfile
import copy
import os
import re
from collections import Counter

from cutevariant.core import sql
from cutevariant.core.reader import BedReader
from tests.utils import table_exists, table_count

from cutevariant.core.reader import FakeReader


FIELDS = [
    {
        "name": "chr",
        "category": "variants",
        "type": "str",
        "description": "chromosome",
    },
    {"name": "pos", "category": "variants", "type": "int", "description": "position"},
    {"name": "ref", "category": "variants", "type": "str", "description": "reference"},
    {
        "name": "alt",
        "category": "variants",
        "type": "str",
        "description": "alternative",
    },
    {
        "name": "dp",
        "category": "variants",
        "type": "int",
        "description": "depth ",
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
        "name": "qual",
        "category": "variants",
        "type": "float",
        "description": "Quality of the variant",
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
        "dp": None,
        "extra1": 10,
        "extra2": 100,
        "qual": 15,
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
        "chr": "chr1",
        "pos": 50,
        "ref": "C",
        "alt": "C",
        "dp": 100,
        "extra1": 20,
        "extra2": 100,
        "qual": 20,
        "annotations": [{"gene": "gene1", "transcript": "transcript1"}],
    },
    {
        "chr": "chr1",
        "pos": 45,
        "ref": "G",
        "alt": "A",
        "dp": 100,
        "extra1": 20,
        "extra2": 100,
        "qual": 7,
        "annotations": [{"gene": "gene2", "transcript": "transcript2"}],
        "samples": [
            {"name": "sacha", "gt": 0, "dp": 30},
            {"name": "boby", "gt": 0, "dp": 70},
        ],
    },
]

VARIANTS_FOR_UPDATE = [
    {
        "chr": "chr1",
        "pos": 10,
        "ref": "G",
        "alt": "A",
        "extra1": 9001,
        "extra2": 9002,
        "qual": 15,
        "newCol": "newAnnot",
        "annotations": [
            {"gene": "gene1", "transcript": "NEWTRANSCRIPT"},
            {"gene": "gene1", "transcript": "transcript2"},
            {"gene": "gene1", "transcript": "transcript2", "cnomen": "cnomen3"},
        ],
        "samples": [
            {"name": "sacha", "gt": 1, "dp": 75},
            {"name": "boby", "gt": 1, "dp": 15},
        ],
    },
    {
        "chr": "chr2",
        "pos": 9000,
        "ref": "C",
        "alt": "G",
        "dp": 100,
        "extra1": 20,
        "extra2": 100,
        "qual": 20,
        "annotations": [{"gene": "gene1", "transcript": "transcript1"}],
        "samples": [
            {"name": "sacha", "gt": 1, "dp": 40},
            {"name": "boby", "gt": 1, "dp": 35},
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


def test_create_database_schema():

    conn = sql.get_sql_connection(":memory:")
    sql.create_database_schema(conn)

    assert sql.table_exists(conn, "variants")
    assert sql.table_exists(conn, "fields")
    assert sql.table_exists(conn, "annotations")
    assert sql.table_exists(conn, "samples")
    assert sql.table_exists(conn, "genotypes")
    assert sql.table_exists(conn, "selections")
    assert sql.table_exists(conn, "wordsets")


def test_alter_table():
    conn = sql.get_sql_connection(":memory:")
    sql.create_database_schema(conn)
    columns_before = sql.get_table_columns(conn, "variants")
    fields = [{"name": "boby", "type": "str"}]
    sql.alter_table(conn, "variants", fields)
    columns_after = sql.get_table_columns(conn, "variants")
    assert columns_after == columns_before + [fields[0]["name"]]


def test_get_clean_fields():
    """Test if missing fields are added"""
    fields = [{"name": "boby", "type": "str", "category": "variants"}]
    fields = [f["name"] for f in sql.get_clean_fields(fields)]

    assert "chr" in fields
    assert "pos" in fields


def test_get_accepted_fields():
    """Test if missing fields are added"""
    fields = [
        {"name": "boby", "type": "str", "category": "variants"},
        {"name": "charles", "type": "str", "category": "variants"},
    ]

    ignored_fields = [
        {"name": "charles", "type": "str", "category": "variants"},
    ]

    assert len(sql.get_accepted_fields(fields, [])) == 2

    fields = [f["name"] for f in sql.get_accepted_fields(fields, ignored_fields)]

    assert "charles" not in fields
    assert "boby" in fields


def test_get_clean_variants():
    """Test if missing variant key are added"""
    variants = [{"chr": "chr3", "pos": 324234, "ref": "A", "alt": "C"}]
    variant = next(sql.get_clean_variants(variants))

    assert variant["is_snp"] == True


def test_alter_table_by_fields():
    conn = sql.get_sql_connection(":memory:")
    sql.create_database_schema(conn)
    fields = sql.get_table_columns(conn, "variants")

    new_fields = [{"name": "test", "type": "str", "category": "variants"}]
    sql.alter_table_from_fields(conn, new_fields)

    observed = sql.get_table_columns(conn, "variants")
    expected = fields + [i["name"] for i in new_fields]

    assert observed == expected


def test_import_reader():
    fd, filepath = tempfile.mkstemp()
    conn = sql.get_sql_connection(filepath)

    reader = FakeReader()
    sql.import_reader(conn, reader)


# def test_import_variants():
#     try:
#         os.remove("/tmp/cutetest.db")
#     except:
#         pass
#     conn = sql.get_sql_connection("/tmp/cutetest.db")
#     sql.create_database_schema(conn)
#     sql.insert_samples(conn, SAMPLES)

#     sql.insert_variants(conn, VARIANTS)
# sql.insert_variants(conn, VARIANTS_FOR_UPDATE)


# def test_insert_variants():
#     conn = sql.get_sql_connection(":memory:")
#     sql.create_database_schema(conn)

#     sql.insert_variants_async(conn, VARIANTS)


@pytest.fixture
def conn():
    """Initialize a memory DB with test data and return a connexion on this DB"""
    conn = sql.get_sql_connection(":memory:")

    assert sql.schema_exists(conn) == False

    sql.create_database_schema(conn)

    assert sql.schema_exists(conn) == True

    sql.alter_table(
        conn, "variants", [field for field in FIELDS if field["category"] == "variants"]
    )
    sql.alter_table(
        conn,
        "annotations",
        [field for field in FIELDS if field["category"] == "annotations"],
    )
    sql.alter_table(
        conn,
        "genotypes",
        [field for field in FIELDS if field["category"] == "samples"],
    )

    sql.update_project(conn, {"name": "test", "reference": "hg19"})
    assert table_exists(conn, "projects"), "cannot create table projects"
    project_data = sql.get_project(conn)
    assert project_data["name"] == "test"
    assert project_data["reference"] == "hg19"

    assert table_exists(conn, "fields"), "cannot create table fields"

    sql.insert_fields(conn, copy.deepcopy(FIELDS))

    assert table_count(conn, "fields") == len(FIELDS), "cannot insert many fields"

    assert table_exists(conn, "selections"), "cannot create table selections"

    assert table_exists(conn, "annotations"), "cannot create table annotations"

    assert table_exists(conn, "samples"), "cannot create table samples"
    sql.insert_samples(conn, copy.deepcopy(SAMPLES))

    assert table_exists(conn, "variants"), "cannot create table variants"
    sql.insert_variants(conn, copy.deepcopy(VARIANTS))
    assert table_exists(conn, "wordsets"), "cannot create table sets"

    sql.create_table_tags(conn)
    assert table_exists(conn, "tags"), "cannot create table tags"

    return conn


@pytest.fixture
def variants_data():
    """Secured variants that will not be modified from a test to another"""
    return copy.deepcopy(VARIANTS)


@pytest.fixture
def kindly_wordset_fixture():
    """Yes its ugly but i don't know how to use a fixture in parametrize"""
    return kindly_wordset()


def kindly_wordset():
    """Return filepath + expected data of a word set that contains 4 genes"""
    fd, filepath = tempfile.mkstemp()
    data = ["gene1", "gene2", "KRAS", "BRCA1"]

    # Simulate a file with a list of genes (1 per line)
    with open(filepath, "w") as f_h:
        f_h.write("\n".join(data))

    os.close(fd)
    return filepath, data


def hasardous_wordset():
    """Return filepath + expected data of a word set that contains 1 gene
    and malformed biologistic data.

    Notes:
        Empty lines, whitespaces in line
    """
    fd, filepath = tempfile.mkstemp()
    data = ["gene2", "E.Micron", "xyz\r\n", "abc  def\tghi\t  \r\n"]

    # Simulate a file with a list of genes (1 per line)
    with open(filepath, "w") as f_h:
        f_h.write("\n".join(data))
    os.close(fd)
    return filepath, data[:2] + ["xyz"]


def print_table_for_debug(conn, table):
    print("\nTABLE:", table)
    cur = conn.cursor()
    with conn:
        cur.execute("SELECT * FROM " + table)
        for row in cur.fetchall():
            print(tuple(row))


################################################################################

# def test_update(conn):
#     #TODO: automate table update verification
#     for table in ("variants", "annotations", "samples", "genotypes", "selections"):
#         print_table_for_debug(conn, table)
#     for x, y in sql.update_variants_async(conn,
#                             VARIANTS_FOR_UPDATE,
#                             total_variant_count=len(VARIANTS_FOR_UPDATE),
#                             yield_every=1):
#         print(x,y)
#     for table in ("variants", "annotations", "samples", "genotypes", "selections"):
#         print_table_for_debug(conn, table)


def test_update_variants_counts(conn):

    sql.update_variants_counts(conn)

    samples = VARIANTS[0]["samples"]

    expected = {}
    expected["count_var"] = sum(sample["gt"] for sample in samples if sample["gt"] > 1)
    expected["count_het"] = sum(sample["gt"] for sample in samples if sample["gt"] == 1)
    expected["count_hom"] = sum(sample["gt"] for sample in samples if sample["gt"] == 2)
    expected["count_ref"] = sum(sample["gt"] for sample in samples if sample["gt"] == 0)

    observed = dict(
        conn.execute(
            "SELECT count_var, count_het, count_hom, count_ref FROM variants WHERE id = 1"
        ).fetchone()
    )

    assert expected == observed


def test_get_samples_from_query(conn):

    # Update database with complete sample information to test
    # TODO: Have richer conn fixture to have more testability
    sql.update_sample(conn, {"id": 1, "classification": 4, "sex": 0, "phenotype": 1})
    sql.update_sample(conn, {"id": 2, "classification": 2, "sex": 0, "phenotype": 0})

    assert len(list(sql.get_samples_from_query(conn, "boby"))) == 1

    assert len(list(sql.get_samples_from_query(conn, ""))) == len(list(sql.get_samples(conn)))
    assert len(list(sql.get_samples_from_query(conn, "id:1"))) == 1

    query = "classification:3,4 sex:0 phenotype:1"
    assert next(sql.get_samples_from_query(conn, query)) == {
        "id": 1,
        "name": "sacha",
        "family_id": "fam",
        "father_id": 0,
        "mother_id": 0,
        "sex": 0,
        "phenotype": 1,
        "classification": 4,
        "tags": "",
        "comment": "",
    }


def test_create_indexes(conn):

    VARIANT_IDX = ["dp"]
    ANN_IDX = ["gene"]
    SAMPLE_IDX = ["gt"]
    sql.create_indexes(
        conn,
        indexed_variant_fields=VARIANT_IDX,
        indexed_annotation_fields=ANN_IDX,
        indexed_sample_fields=SAMPLE_IDX,
    )

    # test if index exists
    idx = [
        re.sub(r"idx_\w+_", "", dict(idx)["name"])
        for idx in conn.execute("SELECT name FROM sqlite_master WHERE type='index'")
    ]

    assert len(set(VARIANT_IDX) & set(idx)) == len(VARIANT_IDX)
    assert len(set(ANN_IDX) & set(idx)) == len(ANN_IDX)
    assert len(set(SAMPLE_IDX) & set(idx)) == len(SAMPLE_IDX)


def test_list_indexes(conn: sqlite3.Connection):
    VARIANT_IDX = {"dp"}
    ANN_IDX = {"gene"}
    SAMPLE_IDX = {"gt"}
    sql.create_indexes(
        conn,
        indexed_variant_fields=VARIANT_IDX,
        indexed_annotation_fields=ANN_IDX,
        indexed_sample_fields=SAMPLE_IDX,
    )

    indexes = sql.get_indexed_fields(conn)

    indexed_fields = {"variants": [], "annotations": [], "samples": []}
    for cat, field in indexes:
        indexed_fields[cat].append(field)

    assert set(indexed_fields["variants"]) == set(VARIANT_IDX)
    assert set(indexed_fields["annotations"]) == set(ANN_IDX)
    assert set(indexed_fields["samples"]) == set(SAMPLE_IDX)


def test_remove_index(conn: sqlite3.Connection):
    VARIANT_IDX = {"dp", "extra1", "extra2"}
    ANN_IDX = {"gene", "transcript"}
    SAMPLE_IDX = {"gt", "dp"}

    sql.create_indexes(
        conn,
        indexed_variant_fields=VARIANT_IDX,
        indexed_annotation_fields=ANN_IDX,
        indexed_sample_fields=SAMPLE_IDX,
    )

    indexes = sql.get_indexed_fields(conn)
    # extra1 was inserted
    assert ("variants", "extra1") in indexes
    sql.remove_indexed_field(conn, "variants", "extra1")
    indexes = sql.get_indexed_fields(conn)
    # extra1 was removed
    assert ("variants", "extra1") not in indexes

    indexes = sql.get_indexed_fields(conn)
    # extra1 was inserted
    assert ("annotations", "transcript") in indexes
    sql.remove_indexed_field(conn, "annotations", "transcript")
    indexes = sql.get_indexed_fields(conn)
    # extra1 was removed
    assert ("annotations", "transcript") not in indexes

    indexes = sql.get_indexed_fields(conn)
    # extra1 was inserted
    assert ("samples", "gt") in indexes
    sql.remove_indexed_field(conn, "samples", "gt")
    indexes = sql.get_indexed_fields(conn)
    # extra1 was removed
    assert ("samples", "gt") not in indexes


@pytest.mark.parametrize("field", ["pos", "qual"])
def test_get_field_info(conn, field):
    # TODO ...
    metrics = ["min", "max", "median", "mean", "q1", "q3"]
    # stats = sql.get_field_info(conn, field, metrics)
    # TODO ....
    # assert sorted(list(stats.keys())) == sorted(metrics)

    # This test still needs improvement but at least kinda works...


def test_create_connexion(conn):
    assert conn is not None


def test_update_project(conn):

    project_data = sql.get_project(conn)

    assert project_data["name"] == "test"
    assert project_data["reference"] == "hg19"

    sql.update_project(conn, {"name": "test2", "extra": 324})
    project_data = sql.get_project(conn)
    assert project_data["name"] == "test2"
    assert project_data["reference"] == "hg19"
    assert project_data["extra"] == "324"

    assert sql.count_query(conn, "SELECT * FROM projects") == 3


def test_get_database_file_name():
    dbfile_name = tempfile.mkstemp()[1]
    conn = sql.get_sql_connection(dbfile_name)
    returned_file_name = sql.get_database_file_name(conn)
    assert dbfile_name == returned_file_name


def test_columns(conn):
    # Test if variant fields is in databases
    q = conn.execute("PRAGMA table_info(variants)")
    variant_fields = [record[1] for record in q]

    q = conn.execute("PRAGMA table_info(annotations)")
    annotation_fields = [record[1] for record in q]

    q = conn.execute("PRAGMA table_info(genotypes)")
    sample_fields = [record[1] for record in q]

    for field in FIELDS:

        if field["category"] == "variants":
            assert field["name"] in variant_fields

        if field["category"] == "annotations":
            assert field["name"] in annotation_fields

        if field["category"] == "samples":
            assert field["name"] in sample_fields


def test_get_columns(conn):
    """Test getting columns of variants and annotations"""
    variant_cols = set(sql.get_table_columns(conn, "variants"))
    expected_cols = {i["name"] for i in FIELDS if i["category"] == "variants"}
    extra_cols = {i["name"] for i in sql.MANDATORY_FIELDS if i["category"] == "variants"}
    assert variant_cols == expected_cols.union(extra_cols)

    annot_cols = set(sql.get_table_columns(conn, "annotations"))
    expected_cols = {i["name"] for i in FIELDS if i["category"] == "annotations"}
    expected_cols.add("variant_id")
    # {'gene', 'transcript', 'variant_id'}
    assert annot_cols == expected_cols


def test_get_annotations(conn):
    """Compare annotations from DB with expected annotations for each variant

    Interrogation of `annotations` table.
    """

    for index, variant in enumerate(VARIANTS):
        read_tx = list(sql.get_annotations(conn, index + 1))[0]
        del read_tx["variant_id"]
        expected_tx = VARIANTS[index]["annotations"][0]

        assert read_tx == expected_tx


def test_get_genotypes(conn):

    expected = [
        dict(i, variant_id=1, sample_id=index + 1) for index, i in enumerate(VARIANTS[0]["samples"])
    ]
    observed = []
    for i in sql.get_genotypes(conn, 1, fields=["gt", "dp"]):
        observed.append(i)

    assert len(expected) == len(observed)

    observed.clear()
    for i in sql.get_genotypes(conn, 1, fields=["gt", "dp"], samples=["sacha"]):
        observed.append(i)

    print(observed)
    assert len(observed) == 1


def test_get_histories(conn):

    new_classification = 10
    sql.update_variant(conn, {"id": 1, "classification": new_classification})
    sql.update_sample(conn, {"id": 1, "classification": new_classification})

    for table in ("variants", "samples"):
        record = next(sql.get_histories(conn, table, 1))
        assert record["field"] == "classification"
        assert record["before"] == "0"
        assert record["after"] == str(new_classification)


def test_get_sample_annotations(conn, variants_data):
    """Compare sample annotations from DB with expected samples annotations

    Interrogation of `genotypes` table
    """
    for variant_id, variant in enumerate(variants_data, 1):
        if "samples" in variant:
            for sample_id, sample in enumerate(variant["samples"], 1):
                result = sql.get_sample_annotations(conn, variant_id, sample_id)
                del result["sample_id"]
                del result["variant_id"]
                del result["classification"]
                del sample["name"]

                sample["comment"] = ""
                sample["tags"] = ""
                # This field is in samples table
                assert result == sample


def test_get_fields(conn):
    """Test the correct insertion of fields in DB"""
    for index, f in enumerate(sql.get_fields(conn)):
        rowid = f.pop("id")
        assert f == FIELDS[index]
        assert index + 1 == rowid


def test_get_variants(conn):
    """More complexe query are actually tested from query builder"""

    fields = ["chr", "pos", "ref", "alt", "ann.gene"]

    for variant in sql.get_variants(conn, fields):
        print(variant)
        for field in fields:
            assert field in variant


def test_get_variant_as_group(conn):
    # TODO : make test better with different group_by
    # Currently, it only tests genes
    group_by = "gene"
    fields = ["chr", "pos", "ref", "alt", "ann.gene"]

    # Compute expected
    # Takes duplicate into account
    # This is ugly.. need to refactor
    expected_genes = Counter()
    for variant in VARIANTS:
        if "annotations" in variant:
            fields_to_count = set()
            for ann in variant["annotations"]:
                if "gene" in ann:
                    fields_to_count.add(ann[group_by])
            for g in fields_to_count:
                expected_genes[g] += 1

    observed_genes = dict(
        [
            (i["ann." + group_by], i["count"])
            for i in sql.get_variant_as_group(conn, "ann." + group_by, fields, "variants", {})
        ]
    )

    assert observed_genes == expected_genes


def test_get_samples(conn):
    """Test default values of samples"""
    assert [sample["name"] for sample in sql.get_samples(conn)] == SAMPLES
    first_sample = list(sql.get_samples(conn))[0]

    # test default value
    assert first_sample["name"] == "sacha"
    assert first_sample["family_id"] == "fam"
    assert first_sample["father_id"] == 0
    assert first_sample["mother_id"] == 0
    assert first_sample["sex"] == 0
    assert first_sample["phenotype"] == 0


def test_update_samples(conn):
    """Test update procedure of a sample in DB (modify some of its field values)"""
    previous_sample = list(sql.get_samples(conn))[0]

    assert previous_sample["name"] == "sacha"
    assert previous_sample["id"] == 1
    # Update with info
    previous_sample["name"] = "maco"
    previous_sample["family_id"] = "fam2"
    previous_sample["father_id"] = 1
    previous_sample["mother_id"] = 1
    previous_sample["sex"] = 2
    previous_sample["phenotype"] = 2

    # Update the sample
    sql.update_sample(conn, previous_sample)

    # Get the updated sample
    edit_sample = list(sql.get_samples(conn))[0]
    # The sample in DB must be the same than the sample we modified above
    assert previous_sample == edit_sample


def test_update_variant(conn):
    """Test update procedure of a variant in DB (modify some of its field values)

    .. note:: exception si pas id, ajout comment
    """
    # Update the first variant data
    updated = {"id": 1, "ref": "A", "chr": "chrX"}
    sql.update_variant(conn, updated)

    inserted = sql.get_variant(conn, 1)

    assert inserted["ref"] == updated["ref"]
    assert inserted["chr"] == updated["chr"]


@pytest.mark.parametrize(
    "wordset",
    (kindly_wordset(), hasardous_wordset()),
    ids=["kindly_wordset", "hasardous_wordset"],
)
def test_insert_set_from_file(conn, wordset):
    """Test the insertion of gene names from file into the database

    Simulation of problematic data from biologists is made via hasardous_wordset
    """
    wordset_file, expected_data = wordset

    print("Expected data:", expected_data)

    sql.insert_wordset_from_file(conn, "test_wordset", wordset_file)

    # TODO: for now the one to many relation is not implemented
    # All records have the name of the set... awesome
    for record in conn.execute("SELECT * FROM wordsets").fetchall():
        record = dict(record)
        print("Found record:", record)
        assert record["name"] == "test_wordset"
        assert record["value"] in expected_data

    # os.remove(wordset_file)


def test_insert_set_from_list(conn):

    expected = set(["CFTR", "GJB2"])
    sql.insert_wordset_from_list(conn, "name", expected)
    observed = set([i["value"] for i in conn.execute("SELECT * FROM wordsets").fetchall()])

    assert expected == observed


def test_get_sets(conn, kindly_wordset_fixture):
    """Test get_wordsets: Word set group by results"""
    wordset_file, _ = kindly_wordset_fixture

    sql.insert_wordset_from_file(conn, "test_wordset", wordset_file)

    expected = [{"name": "test_wordset", "count": 4}]
    found = list(sql.get_wordsets(conn))

    assert expected == found

    os.remove(wordset_file)


@pytest.mark.parametrize(
    "wordset",
    (kindly_wordset(), hasardous_wordset()),
    ids=["kindly_wordset", "hasardous_wordset"],
)
def test_get_words_in_set(conn, wordset):
    """Test the query of gene names stored into a word set in DB

    Simulation of problematic data from biologists is made via hasardous_wordset
    """
    wordset_file, expected_data = wordset

    print("Expected data:", expected_data)

    sql.insert_wordset_from_file(conn, "test_wordset", wordset_file)

    found = set(sql.get_wordset_by_name(conn, "test_wordset"))

    assert set(expected_data) == found

    # os.remove(wordset_file)


def test_wordset_operation(conn):
    """Test wordset operation union, intersection and difference"""
    set1 = {"CFTR", "GJB2"}
    set2 = {"CFTR", "KRAS", "BRAF"}

    sql.insert_wordset_from_list(conn, "A", set1)
    sql.insert_wordset_from_list(conn, "B", set2)

    sql.insert_wordset_from_intersect(conn, "C", ["A", "B"])
    sql.insert_wordset_from_union(conn, "D", ["A", "B"])
    sql.insert_wordset_from_subtract(conn, "E", ["A", "B"])

    assert set(sql.get_wordset_by_name(conn, "C")) == set1 & set2
    assert set(sql.get_wordset_by_name(conn, "D")) == set1 | set2
    assert set(sql.get_wordset_by_name(conn, "E")) == set1 - set2


def test_selections(conn):
    """Test the creation of a full selection in "selection_has_variant"
    and "selections" tables; Test also the ON CASCADE deletion of rows in
    "selection_has_variant" when a selection is deleted.
    """

    # Create a selection that contains all 8 variants in the DB
    # (no filter on this list, via annotation table because this table is not
    # initialized here)
    query = """SELECT variants.id,chr,pos,ref,alt FROM variants
       LEFT JOIN annotations
        ON annotations.variant_id = variants.rowid"""

    # Create a new selection (a second one, since there is a default one during DB creation)
    ret = sql.insert_selection_from_sql(conn, query, "selection_name", count=None)
    assert ret == 2

    # Query the association table (variant_id, selection_id)
    data = conn.execute("SELECT * FROM selection_has_variant")
    expected = ((1, ret), (2, ret), (3, ret))
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
    assert conn.in_transaction
    conn.commit()
    assert not conn.in_transaction


# def test_selection_operation(conn):
#    """test set operations on selections
#    PS: try to handle precedence of operators"""
#
#    # Select all
#    query = """SELECT variants.id,chr,pos,ref,alt FROM variants"""
#    id_all = sql.create_selection_from_sql(conn, query, "all", count=None)
#
#    # Select only ref = C (4 variants)
#    query = """SELECT variants.id,chr,pos,ref,alt FROM variants WHERE ref='C'"""
#    id_A = sql.create_selection_from_sql(conn, query, "setA", count=None,)
#
#    # Select only alt = C (2 variants among setA)
#    query = """SELECT variants.id,chr,pos,ref,alt FROM variants WHERE alt='C'"""
#    id_B = sql.create_selection_from_sql(conn, query, "setB", count=None)
#
#    assert all((id_all, id_A, id_B))
#
#    selections = [selection["name"] for selection in sql.get_selections(conn)]
#
#    assert "setA" in selections
#    assert "setB" in selections
#    raise NotImplementedError

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


def test_get_one_variant(conn):
    """Test getting variant from variant_id

    .. note:: annotations and samples which are optional are not tested here
        => see :meth:`test_advanced_get_one_variant`
    """
    for variant_id, expected_variant in enumerate(VARIANTS, 1):
        found_variant = sql.get_variant(conn, variant_id)

        print("found variant", found_variant)
        assert found_variant["id"] == variant_id

        for k, v in expected_variant.items():
            if k not in ("annotations", "samples"):
                print(k)
                assert found_variant[k] == expected_variant[k]


def test_advanced_get_one_variant(conn):
    """Test getting variant from variant_id

    .. note:: annotations and samples which are optional ARE tested here
    """
    for variant_id, expected_variant in enumerate(VARIANTS, 1):
        found_variant = sql.get_variant(conn, variant_id, with_annotations=True, with_samples=True)

        for extra_field in ("annotations", "samples"):

            assert isinstance(found_variant[extra_field], list), "Type not expected"

            for item in found_variant[extra_field]:
                # Remove variant_id and sample_id from sample/annotation before test
                if "variant_id" in item:
                    del item["variant_id"]

                if "sample_id" in item:
                    del item["sample_id"]

                if "tags" in item:
                    del item["tags"]

                if "classification" in item:
                    del item["classification"]

                if "comment" in item:
                    del item["comment"]

            if extra_field in found_variant and extra_field in expected_variant:
                assert found_variant[extra_field] == expected_variant[extra_field]


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

    bedtool = BedReader(larger_string)

    # Create a new selection (a second one, since there is a default one during DB creation)
    selection_name = "bedname"
    ret = sql.insert_selection_from_bed(conn, "variants", selection_name, bedtool)

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
    larger_string = """
        chr1 1    10   feature1  0 +
        chr1 50   60   feature2  0 -
        chr1 51 59 another_feature 0 +
    """
    # According to VARIANTS global variable with 3 variants (pos 10, 50 and 45)
    # 1: chr1, pos 1 to 10 => 1 variant concerned (pos 10)
    # 2: chr1, pos 50 to 60 => 1 variant concerned (pos 50)
    # 3: chr1, pos 51 to 59 => 0 variants
    bedtool = BedReader(larger_string)

    # Create now a sub selection => 2 variants (pos 10, 45)
    query = "SELECT variants.id,chr,pos,ref,alt FROM variants WHERE ref='G'"
    set_A_id = sql.insert_selection_from_sql(conn, query, "setA", count=None)
    # 2nd selection (1st is the default "variants")
    assert set_A_id == 2
    assert "setA" in list(s["name"] for s in sql.get_selections(conn))

    # 1: chr1, pos 1 to 10 => 1 remaining variant
    # 2: chr1, pos 50 to 60 => 0 variant
    # 3: chr1, pos 51 to 59 => 0 variant
    ret = sql.insert_selection_from_bed(conn, "setA", "sub_bedname", bedtool)
    # id of selection
    assert ret == 3

    data = conn.execute("SELECT * FROM selection_has_variant WHERE selection_id = ?", (ret,))
    expected = ((1, ret),)
    record = tuple([tuple(i) for i in data])
    assert record == expected


def test_sql_selection_operation(conn):
    """Test set operations on selections using SQL API

    .. Todo:: Only union is tested here test intersect and expect
        (intersect is tested in test_command)
    """
    cursor = conn.cursor()

    # Query the first default selection
    all_selection = cursor.execute("SELECT * FROM selections").fetchone()

    # {'id': 1, 'name': 'variants', 'count': 3, 'query': ''}
    print("all", dict(all_selection))
    # index 0: id in db
    assert all_selection[1] == "variants"
    assert all_selection[2] == len(VARIANTS)

    # Create a selection from sql
    query = "SELECT id, chr, pos FROM variants where alt = 'A' "
    sql.insert_selection_from_sql(conn, query, "test")

    # check if selection has been created
    assert "test" in [record["name"] for record in sql.get_selections(conn)]

    # Check if selection of variants returns same data than selection query
    selection_id = 2
    insert_data = cursor.execute(query).fetchall()

    read_data = cursor.execute(
        f"""
        SELECT variants.id, variants.chr, variants.pos FROM variants
        INNER JOIN selection_has_variant sv ON variants.rowid = sv.variant_id AND sv.selection_id = {selection_id}
        """
    ).fetchall()

    # set because, it can contains duplicate variants
    assert set(read_data) == set(insert_data)

    # TEST Unions
    query1 = "SELECT id, chr, pos FROM variants where alt = 'A' "  # 2 variants
    query2 = "SELECT id, chr, pos FROM variants where alt = 'C' "  # 1 variant

    union_query = sql.union_variants(query1, query2)
    print(union_query)
    selection_id = sql.insert_selection_from_sql(conn, union_query, "union_GT")
    print("union_GT selection id: ", selection_id)
    assert selection_id is not None
    record = cursor.execute(f"SELECT id, name FROM selections WHERE name = 'union_GT'").fetchone()
    print("Found record:", dict(record))
    selection_id = record[0]
    selection_name = record[1]
    assert selection_id == 3  # test if selection id equal 2 ( the first is "variants")
    assert selection_name == "union_GT"

    # Select statement from union_GT selection must contains only variant.alt G or T
    records = cursor.execute(
        f"""
        SELECT variants.chr, variants.pos, variants.ref, variants.alt FROM variants
        INNER JOIN selection_has_variant sv ON variants.rowid = sv.variant_id AND sv.selection_id = {selection_id}
        """
    ).fetchall()

    # {'chr': 'chr1', 'pos': 10, 'ref': 'G', 'alt': 'A'}
    # {'chr': 'chr1', 'pos': 50, 'ref': 'C', 'alt': 'C'}
    # {'chr': 'chr1', 'pos': 45, 'ref': 'G', 'alt': 'A'}
    for found_variants, record in enumerate(records, 1):
        print(dict(record))
        assert record["alt"] in ("A", "C")

    assert found_variants == 3


# def test_variants(conn):
#     """Test that we have all inserted variants in the DB"""

#     for i, record in enumerate(conn.execute("SELECT * FROM variants")):
#         record = list(record)[1:]  # omit id
#         expected_variant = VARIANTS[i]

#         # Check only variants, not annotations or samples
#         for not_wanted_key in ("annotations", "samples"):
#             if not_wanted_key in expected_variant:
#                 del expected_variant[not_wanted_key]
#         assert tuple(record) == tuple(expected_variant.values())


def test_get_sample_variant_classification_count(conn):
    value = sql.get_sample_variant_classification_count(conn, 1, 2)
    assert value == 0
    sql.update_genotypes(conn, {"variant_id": 1, "sample_id": 1, "classification": 2})
    value = sql.get_sample_variant_classification_count(conn, 1, 2)
    assert value == 1
