from cutevariant.core.reader.abstractreader import AbstractReader
from cutevariant.core import sql
from tests import utils


class TestReader(AbstractReader):
    def __init__(self, variants, fields, samples):
        super().__init__(None)

        self.variants = variants
        self.fields = fields
        self.samples = samples

    def get_variants(self):
        return self.variants

    def get_fields(self):
        return self.fields

    def get_samples(self):
        return self.samples


def import_data(conn, variants, fields, samples):
    reader = TestReader(variants, fields, samples)
    sql.import_reader(conn, reader)


# ========= FAKE READER 1 =========

FIELDS = [
    {
        "name": "chr",
        "category": "variants",
        "description": "chromosom",
        "type": "str",
        "constraint": "NOT NULL",
    },
    {
        "name": "pos",
        "category": "variants",
        "description": "position",
        "type": "int",
        "constraint": "NOT NULL",
    },
    {
        "name": "ref",
        "category": "variants",
        "description": "reference base",
        "type": "str",
        "constraint": "NOT NULL",
    },
    {
        "name": "alt",
        "category": "variants",
        "description": "alternative base",
        "type": "str",
        "constraint": "NOT NULL",
    },
    {
        "name": "qual",
        "category": "variants",
        "description": "",
        "type": "int",
    },
    {
        "name": "gt",
        "category": "samples",
        "description": "genotype",
        "type": "int",
    },
    {
        "name": "transcript",
        "category": "annotations",
        "description": "gene transcripts",
        "type": "str",
    },
]

VARIANT = {
    "chr": "1",
    "pos": 11000,
    "ref": "T",
    "alt": "A",
    "qual": 30,
    "annotations": [
        {"transcript": "NM_234234"},
        {"transcript": "NM_234235"},
    ],
    "samples": [{"name": "sacha", "gt": 1}, {"name": "charles", "gt": 1}],
}


SAMPLES = ["sacha", "charles"]


def test_import_new_variants():
    """
    Testing if new samples if append
    """
    conn = sql.get_sql_connection(":memory:")

    #  Import first reader
    variants = []
    new_variants = []
    variant_count = 5
    for i in range(variant_count):
        variants.append(VARIANT.copy())
        new_variants.append(VARIANT.copy())

        variants[i]["pos"] = i
        new_variants[i]["chr"] = str(i)

    import_data(conn, variants, FIELDS, SAMPLES)

    assert utils.table_count(conn, "variants") == variant_count

    import_data(conn, new_variants, FIELDS, SAMPLES)

    assert utils.table_count(conn, "variants") == variant_count * 2


def test_import_update_info_variants():
    """
    Import 5 variants
    Import one same variant with qual = 999

    """

    conn = sql.get_sql_connection(":memory:")
    variants = []
    variant_count = 5
    for i in range(variant_count):
        variants.append(VARIANT.copy())
        variants[i]["pos"] = i

    import_data(conn, variants, FIELDS, SAMPLES)
    assert utils.table_count(conn, "variants") == variant_count

    ## Add same variants
    import_data(conn, variants, FIELDS, SAMPLES)
    assert utils.table_count(conn, "variants") == variant_count

    # Add different variants
    new_variants = variants[:1]
    new_variants[0]["qual"] = 999
    import_data(conn, new_variants, FIELDS, SAMPLES)
    assert utils.table_count(conn, "variants") == variant_count

    # check if the first variant has been updated
    assert sql.get_variant(conn, 1)["qual"] == 999


def test_import_update_annotation_variants():
    conn = sql.get_sql_connection(":memory:")
    variants = []
    variant_count = 5
    for i in range(variant_count):
        variants.append(VARIANT.copy())
        variants[i]["pos"] = i

    import_data(conn, variants, FIELDS, SAMPLES)

    # Add different variants with new annitations
    new_variants = variants[:1]
    new_variants[0]["annotations"] = [{"transcript": "NM_new_annotation"}]

    import_data(conn, new_variants, FIELDS, SAMPLES)
    assert utils.table_count(conn, "variants") == variant_count

    variant = sql.get_variant(conn, 1, with_annotations=True)

    annotations = variant["annotations"]
    assert len(annotations) == 1
    assert annotations[0]["transcript"] == new_variants[0]["annotations"][0]["transcript"]


def test_import_new_samples():

    conn = sql.get_sql_connection(":memory:")
    variants = []
    new_variants = []

    # Create 2 variants and first import
    for i in range(2):
        variants.append(VARIANT.copy())
        variants[i]["pos"] = i

    import_data(conn, variants, FIELDS, SAMPLES)

    # Create one new variants
    new_variants.append(VARIANT.copy())
    new_variants[0]["pos"] = 999
    new_variants[0]["samples"] = [{"name": "boby", "gt": 1}]
    import_data(conn, new_variants, FIELDS, ["boby"])

    # Check if new samples
    assert utils.table_count(conn, "variants") == 2 + 1
    assert {i["name"] for i in sql.get_samples(conn)} == {"sacha", "charles", "boby"}

    # Check if genotype is defined for variants
    new_variant = sql.get_variant(conn, 3, with_samples=True)
    assert len(new_variant["samples"]) == 1


def test_import_new_samples_with_null_genotype():

    conn = sql.get_sql_connection(":memory:")
    variants = []
    new_variants = []
    variant_count = 2
    # Create 2 variants and first import
    for i in range(variant_count):
        variants.append(VARIANT.copy())
        variants[i]["pos"] = i

    import_data(conn, variants, FIELDS, SAMPLES)

    # Create one new variants
    new_variants.append(VARIANT.copy())
    new_variants[0]["pos"] = 999
    new_variants[0]["samples"] = [{"name": "boby", "gt": -1}]  # NULL genotype
    import_data(conn, new_variants, FIELDS, ["boby"])

    # Check if new samples
    assert utils.table_count(conn, "variants") == 2 + 1
    # 2 variant for 2 samples in genotype tables ! Not for boby
    assert utils.table_count(conn, "sample_has_variant") == variant_count * 2

    assert {i["name"] for i in sql.get_samples(conn)} == {"sacha", "charles", "boby"}


def test_import_update_genotype_variants():

    conn = sql.get_sql_connection(":memory:")
    variants = []
    new_variants = []

    # Create 2 variants and first import
    for i in range(2):
        variants.append(VARIANT.copy())
        variants[i]["pos"] = i

    import_data(conn, variants, FIELDS, SAMPLES)

    # Create one new variants
    new_variants.append(variants[0])
    new_variants[0]["qual"] = 999
    new_variants[0]["samples"] = [{"name": "sacha", "gt": 2}, {"name": "charles", "gt": -1}]
    import_data(conn, new_variants, FIELDS, SAMPLES)

    # Check if new samples
    assert utils.table_count(conn, "variants") == 2

    variant = sql.get_variant(conn, 1, with_samples=True)

    # Ann : Fix
    # assert variant["qual"] == 999
    names = [i["name"] for i in variant["samples"]]

    # TO FIX
    assert "sacha" in names
    assert "charles" not in names

    # TO FIX
    # Get sacha GT
    # GT : Fix
    assert next(i["gt"] for i in variant["samples"] if i["name"] == "sacha") == 2
