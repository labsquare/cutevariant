import pytest
import sys
import os
import sqlite3
import warnings
from cutevariant.core.importer import import_reader, import_pedfile
from cutevariant.core.reader import VcfReader, FakeReader
from cutevariant.core import sql
import os
from .utils import table_exists

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

    #  This file contains 2 samples : TUMOR and NORMAL
    #  Let's assume this is 2 patients name


# def test_import_file_vcf_gz(conn):
#     path = "exemples/test.vcf.gz"
#     import_file(conn, path)

# def test_import_file_csv(conn):
#     path = "exemples/test.csv"
#     import_file(conn, path)
