import pytest
import sys
import os
import sqlite3
import warnings
from cutevariant.core.importer import import_reader, import_pedfile, async_import_reader
from cutevariant.core.reader import VcfReader, FakeReader
from cutevariant.core import sql
import os
from .utils import table_exists
import csv

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
    reader = VcfReader(open("examples/test.snpeff.vcf"), "snpeff")
    conn = sqlite3.connect(":memory:")
    import_reader(conn, reader)

    import_pedfile(conn, "examples/test.snpeff.pedigree.tfam")

    print("salut")
    first_sample = dict(next(conn.execute("SELECT * FROM samples")))

    assert first_sample["fam"] == "Fam1"
    assert first_sample["father_id"] == 2
    assert first_sample["mother_id"] == 1
    assert first_sample["sex"] == 2
    assert first_sample["phenotype"] == 1


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
