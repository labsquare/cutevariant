# Standard imports
import pytest
import sqlite3
from collections import OrderedDict

# Custom imports

from cutevariant.core.reader.abstractreader import nullify

from cutevariant.core.reader import VcfReader, FakeReader
from cutevariant.core.reader import BedReader
from cutevariant.core.reader import check_variant_schema, check_field_schema
from cutevariant.core import sql


READERS = [
    FakeReader(),
    VcfReader(open("examples/test.vcf")),
    VcfReader(open("examples/test.vep.vcf"), "vep"),
    VcfReader(open("examples/test.snpeff.vcf"), "snpeff"),
    VcfReader(open("examples/snpeff3.vcf"), "snpeff3"),
]


def test_snpeff3():
    reader = VcfReader(open("examples/snpeff3.vcf"))
    names = [field["name"] for field in reader.get_fields()]
    assert "eff" in names


@pytest.mark.parametrize(
    "reader", READERS, ids=[str(i.__class__.__name__) for i in READERS]
)
def test_fields(reader):
    fields = tuple(reader.get_fields())
    field_names = [f["name"] for f in fields]

    # test mandatory fields name
    assert "chr" in field_names
    assert "pos" in field_names
    assert "ref" in field_names
    assert "alt" in field_names

    # check field schema
    for field in fields:
        check_field_schema(field)

    # test field genotypes
    sample_fields = [
        field["name"] for field in fields if field["category"] == "samples"
    ]
    assert "gt" in sample_fields
    assert "dp" in sample_fields

    # Test if fields are unique per categories
    field_with_categories = [f["name"] + f["category"] for f in fields]
    assert len(field_with_categories) == len(set(field_with_categories))


@pytest.mark.parametrize(
    "reader", READERS, ids=[str(i.__class__.__name__) for i in READERS]
)
def test_extra_fields(reader):
    fields = tuple(reader.get_extra_fields())
    field_names = [f["name"] for f in fields]

    assert "favorite" in field_names
    assert "comment" in field_names
    assert "classification" in field_names
    assert "count_hom" in field_names
    assert "count_ref" in field_names
    assert "count_het" in field_names
    assert "count_var" in field_names
    assert "is_indel" in field_names
    assert "is_snp" in field_names

    ## test to remove the  fields
    if "qual" in field_names and "dp" in field_names:

        reader.ignored_fields = [
            {"name": "qual", "category": "variants"},
            {"name": "dp", "category": "variants"},
        ]

        fields = tuple(reader.get_extra_fields())
        field_names = [f["name"] for f in fields if f["category"] == "variants"]

        assert "qual" not in field_names
        assert "dp" not in field_names


@pytest.mark.parametrize(
    "reader", READERS, ids=[str(i.__class__.__name__) for i in READERS]
)
def test_variants(reader):

    # test if variant field name match name from get_fields
    fields = list(reader.get_fields())
    field_names_from_variant = []
    field_names_from_fields = [f["name"] for f in fields]
    field_of_annotations = [f["name"] for f in fields if f["category"] == "annotations"]
    field_of_samples = [f["name"] for f in fields if f["category"] == "samples"]

    for variant in reader.get_variants():

        assert isinstance(variant, dict)

        # test extra types
        if "annotations" in variant:
            assert isinstance(variant["annotations"], list)

        if "samples" in variant:
            assert isinstance(variant["samples"], list)

            samples_names = [s["name"] for s in variant["samples"]]
            assert sorted(reader.get_samples()) == sorted(samples_names)

        # check variant schema
        check_variant_schema(variant)


@pytest.mark.parametrize(
    "reader", READERS, ids=[str(i.__class__.__name__) for i in READERS]
)
def test_extra_variants(reader):
    def check_value(value: str):
        # check if value is okay !
        if isinstance(value, str):
            assert "%3A" not in value
            assert "%3B" not in value
            assert "%3D" not in value
            assert "%25" not in value
            assert "%2C" not in value
            assert "%0D" not in value
            assert "%0A" not in value
            assert "%09" not in value

    for variant in reader.get_extra_variants():
        assert "comment" in variant
        assert "favorite" in variant
        assert "classification" in variant
        assert variant["favorite"] == False
        assert variant["classification"] == 0

    # test remove fields
    last_variant = variant
    ## remove qual
    reader.ignored_fields = [{"name": "qual", "category": "variants"}]
    for variant in reader.get_extra_variants():
        assert "qual" not in variant
        for key, value in variant.items():
            check_value(value)

    ## remove annotation
    if "annotations" in last_variant:
        if "impact" in last_variant["annotations"][0]:
            reader.ignored_fields = [{"name": "impact", "category": "annotations"}]
            for variant in reader.get_extra_variants():
                for ann in variant["annotations"]:
                    assert "impact" not in ann
                    for key, value in ann.items():
                        check_value(value)

    ## remove sample annotations foxog
    if "samples" in last_variant:
        if "foxog" in last_variant["samples"][0]:
            reader.ignored_fields = [{"name": "foxog", "category": "samples"}]
            for variant in reader.get_extra_variants():
                for sample in variant["samples"]:
                    assert "foxog" not in sample
                    for key, value in sample.items():
                        check_value(value)


@pytest.mark.parametrize(
    "reader", READERS, ids=[str(i.__class__.__name__) for i in READERS]
)
def test_create_db(reader):

    conn = sqlite3.connect(":memory:")

    sql.create_table_fields(conn)
    sql.insert_many_fields(conn, reader.get_fields())
    assert len(list(sql.get_fields(conn))) == len(list(reader.get_fields()))

    sql.create_table_samples(conn, reader.get_fields_by_category("samples"))
    sql.insert_many_samples(conn, reader.get_samples())
    assert len(list(sql.get_samples(conn))) == len(list(reader.get_samples()))

    sql.create_table_annotations(conn, reader.get_fields_by_category("annotations"))
    sql.create_table_variants(conn, reader.get_fields_by_category("variants"))

    sql.create_table_selections(conn)

    sql.insert_many_variants(conn, reader.get_variants())

    # count variant with annotation
    variant_count = len(list(reader.get_variants()))
    assert sql.get_variants_count(conn) == variant_count


def test_bedreader_from_string():
    """Test bed string"""

    large_string = """
        chr1 1    10   feature1  0 +
        chr1 50   60   feature2  0 -
        chr1 51 59 another_feature 0 +
    """
    intervals = tuple(BedReader(large_string))
    expected = (
        OrderedDict(
            [
                ("chrom", "chr1"),
                ("start", "1"),
                ("end", "10"),
                ("name", "feature1"),
                ("score", "0"),
                ("strand", "+"),
                ("thickStart", None),
                ("thickEnd", None),
                ("itemRgb", None),
                ("blockCount", None),
                ("blockSizes", None),
                ("blockStarts", None),
            ]
        ),
        OrderedDict(
            [
                ("chrom", "chr1"),
                ("start", "50"),
                ("end", "60"),
                ("name", "feature2"),
                ("score", "0"),
                ("strand", "-"),
                ("thickStart", None),
                ("thickEnd", None),
                ("itemRgb", None),
                ("blockCount", None),
                ("blockSizes", None),
                ("blockStarts", None),
            ]
        ),
        OrderedDict(
            [
                ("chrom", "chr1"),
                ("start", "51"),
                ("end", "59"),
                ("name", "another_feature"),
                ("score", "0"),
                ("strand", "+"),
                ("thickStart", None),
                ("thickEnd", None),
                ("itemRgb", None),
                ("blockCount", None),
                ("blockSizes", None),
                ("blockStarts", None),
            ]
        ),
    )
    assert intervals == expected


def test_bedreader_from_empty_string():
    """Test bed string with no data at all or just no data after the header"""

    large_string = """
        browser position chr7:127471196-127495720
    """

    bedtool = BedReader(large_string)
    intervals = tuple(bedtool)

    assert intervals == tuple()
    assert bedtool.count == 0

    large_string = ""

    bedtool = BedReader(large_string)
    intervals = tuple(bedtool)

    assert intervals == tuple()
    assert bedtool.count == 0


def test_bedreader_from_file():
    """Test bed data in gz and uncompressed files"""

    bedtool = BedReader("examples/test.bed.gz")
    intervals = tuple(bedtool)
    expected = (
        OrderedDict(
            [
                ("chrom", "chr11"),
                ("start", "10000"),
                ("end", "15000"),
                ("name", None),
                ("score", None),
                ("strand", None),
                ("thickStart", None),
                ("thickEnd", None),
                ("itemRgb", None),
                ("blockCount", None),
                ("blockSizes", None),
                ("blockStarts", None),
            ]
        ),
        OrderedDict(
            [
                ("chrom", "chr11"),
                ("start", "119000"),
                ("end", "123000"),
                ("name", None),
                ("score", None),
                ("strand", None),
                ("thickStart", None),
                ("thickEnd", None),
                ("itemRgb", None),
                ("blockCount", None),
                ("blockSizes", None),
                ("blockStarts", None),
            ]
        ),
        OrderedDict(
            [
                ("chrom", "chr11"),
                ("start", "123002"),
                ("end", "123999"),
                ("name", None),
                ("score", None),
                ("strand", None),
                ("thickStart", None),
                ("thickEnd", None),
                ("itemRgb", None),
                ("blockCount", None),
                ("blockSizes", None),
                ("blockStarts", None),
            ]
        ),
        OrderedDict(
            [
                ("chrom", "chr1"),
                ("start", "0"),
                ("end", "999999"),
                ("name", None),
                ("score", None),
                ("strand", None),
                ("thickStart", None),
                ("thickEnd", None),
                ("itemRgb", None),
                ("blockCount", None),
                ("blockSizes", None),
                ("blockStarts", None),
            ]
        ),
    )

    assert intervals == expected
    assert bedtool.count == 4

    bedtool = BedReader("examples/test_with_headers.bed")
    intervals = tuple(bedtool)

    assert intervals == expected
    assert bedtool.count == 4


def test_nullify():
    variant = {
        "chr": "chr3",
        "filters": "",
        "annotations": [{"gene": "CFTR", "test": ""}],
        "samples": [{"name": "boby", "dp": ""}],
    }

    variant = nullify(variant)

    assert variant["filters"] is None
    assert variant["annotations"][0]["test"] is None
    assert variant["samples"][0]["dp"] is None


# def test_vcf():
#     filename = "exemples/test.vcf"
#     # assert os.path.exists(filename), "file doesn't exists"

#     MAX_VARIANTS = 10
#     GENOTYPE = {"1/1": 2, "1/0": 1, "0/0": 0}

#     # Import using pyvcf
#     with open(filename, "r") as file:
#         other_reader = vcf.Reader(file)
#         fields = [i for i in other_reader.infos]  # Plus tard

#         # Take some variants
#         other_variants = []
#         for i, variant in enumerate(other_reader):
#             other_variants.append(variant)
#             if i >= MAX_VARIANTS:
#                 break

#                 # import using cutevariant
#     with open(filename, "r") as file:
#         my_reader = VcfReader(file)


#         assert my_reader.get_variants_count() == 911
#         assert my_reader.get_samples() == other_reader.samples

#         fields = [f["name"] for f in my_reader.get_fields()]

#         assert "chr" in fields
#         assert "pos" in fields
#         assert "ref" in fields
#         assert "alt" in fields

#         # TODO : test annotation .. Gloups ..

#         # Take some variants


# def test_parse_snpeff():
#     filename = "exemples/test.snpeff.vcf"
#     print("parse snpeff")
#     with open(filename,"r") as file:
#         my_reader = VcfReader(file)

#         print(*my_reader.get_fields())

#         for variant in my_reader.get_variants():
#             print(variant)
#             return


# def test_reader():

#     filename = "examples/test.vcf"
#     with open(filename,"r") as file:
#         my_reader = VcfReader(file)

#         print(list(my_reader.get_fields()))
