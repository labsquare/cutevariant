# Standard imports
import pytest
import sqlite3

# Custom imports
from cutevariant.core.importer import import_reader, import_pedfile, async_import_reader
from cutevariant.core.reader import VcfReader, FakeReader
from cutevariant.core import sql


READERS = [
    FakeReader(),
    VcfReader(open("examples/test.vcf")),
    VcfReader(open("examples/test.snpeff.vcf"), "snpeff"),
    VcfReader(open("examples/test.vep.vcf"), "vep"),
]


@pytest.mark.parametrize(
    "reader", READERS, ids=[str(i.__class__.__name__) for i in READERS]
)
def test_import(reader):
    conn = sqlite3.connect(":memory:")
    import_reader(conn, reader)


def test_import_pedfile():
    """Test import of samples from .tfam PED file"""
    reader = VcfReader(open("examples/test.snpeff.vcf"), "snpeff")
    conn = sqlite3.connect(":memory:")
    import_reader(conn, reader)
    import_pedfile(conn, "examples/test.snpeff.pedigree.tfam")

    samples = [dict(row) for row in conn.execute("SELECT * FROM samples")]
    print("Found samples:", samples)

    expected_first_sample = {
        "id": 1,
        "name": "NORMAL",
        "family_id": "fam",
        "father_id": 2,
        "mother_id": 1,
        "sex": 2,
        "phenotype": 1,
    }
    expected_second_sample = {
        "id": 2,
        "name": "TUMOR",
        "family_id": "fam",
        "father_id": 0,
        "mother_id": 0,
        "sex": 1,
        "phenotype": 2,
    }

    # Third sample is not conform
    assert len(samples) == 2

    assert expected_first_sample in samples
    assert expected_second_sample in samples


def test_import_and_create_counting():
    reader = VcfReader(open("examples/test.snpeff.vcf"), "snpeff")
    pedfile = "examples/test.snpeff.pedigree.tfam"

    conn = sqlite3.connect(":memory:")

    for i, msg in async_import_reader(conn, reader, pedfile):
        print(msg)

    samples = list(sql.get_samples(conn))

    assert samples[0]["phenotype"] == 1
    assert samples[1]["phenotype"] == 2

    for record in conn.execute(
        """SELECT count_hom, count_het, count_ref, control_count_hom,control_count_het, control_count_ref,
        case_count_hom,case_count_het, case_count_ref  FROM variants"""
    ):
        print(dict(record))
        assert record["control_count_ref"] == 1
        assert record["case_count_het"] == 1
        assert record["count_hom"] == 0
        assert record["count_het"] == 1
