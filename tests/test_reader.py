from cutevariant.core.reader import VcfReader, FakeReader
from cutevariant.core.reader import check_variant_schema, check_field_schema
from cutevariant.core import sql
import vcf
import os
import pytest
import sqlite3

READERS = [
FakeReader(),
VcfReader(open("examples/test.vcf")),
VcfReader(open("examples/test.vep.vcf"),"vep"),
VcfReader(open("examples/test.snpeff.vcf"),"snpeff"),
]



@pytest.mark.parametrize(
    "reader", READERS, ids=[str(i.__class__.__name__) for i in READERS]
)
def test_fields(reader):
    fields = list(reader.get_fields())
    field_names = [f["name"] for f in fields]
    # # search if field name are unique
    # assert len(set(field_names)) == len(field_names)

    # test mandatory fields name
    assert "chr" in field_names
    assert "pos" in field_names
    assert "ref" in field_names
    assert "alt" in field_names

    # check field schema 
    for field in fields:
        check_field_schema(field)


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

    print(fields)
    print(field_of_annotations)
    print(field_of_samples)

    for variant in reader.get_variants():

        assert isinstance(variant, dict)

        # test extra types
        if "annotations" in variant:
            assert isinstance(variant["annotations"], list)

        if "samples" in variant:
            assert isinstance(variant["samples"], list)
            samples_names = [s["name"] for s in variant["samples"]]
            print(reader.get_samples())
            assert sorted(reader.get_samples()) == sorted(samples_names)

        # check variant schema 
        check_variant_schema(variant)


@pytest.mark.parametrize(
    "reader", READERS, ids=[str(i.__class__.__name__) for i in READERS]
)
def test_create_db(reader):

    conn = sqlite3.connect(":memory:")

    sql.create_table_fields(conn)
    sql.insert_many_fields(conn, reader.get_fields())
    assert len(list(sql.get_fields(conn))) == len(list(reader.get_fields()))

    sql.create_table_samples(conn)
    sql.insert_many_samples(conn, reader.get_samples())
    assert len(list(sql.get_samples(conn))) == len(list(reader.get_samples()))

    sql.create_table_annotations(conn, reader.get_fields_by_category("annotations"))

    sql.create_table_variants(conn, reader.get_fields_by_category("variants"))
    sql.insert_many_variants(conn, reader.get_variants())


    # count variant with annotation 
    variant_count = 0
    for variant in reader.get_variants():
        variant_count+=1

    assert sql.get_variants_count(conn) == variant_count


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
