import os
from cutevariant.core import get_sql_connection

from cutevariant.core import command, vql, sql

from PySide6.QtCore import *
from PySide6.QtWidgets import *
from PySide6.QtGui import *


def run(database_file_name, vql_query, output, overwrite=False):

    if not overwrite and os.path.isfile(output):
        return -1

    conn = get_sql_connection(database_file_name)

    abca3_variants = list(
        command.select_cmd(
            conn,
            **vql.parse_one_vql(vql_query),
        )
    )

    all_samples = [s["name"] for s in sql.get_samples(conn)]

    with open(output, "w") as f:

        TAB = "\t"
        LF = "\n"

        for variant in abca3_variants:
            chrom = variant["chr"]
            pos = variant["pos"]
            genotypes = sql.get_genotypes(conn, variant["id"], ["gt"], all_samples)
            f.write(
                f"{chrom}{TAB}{pos}{TAB}{variant['ann.gene']}{TAB.join(str(s['gt'] or -1) for s in sorted(genotypes,key=lambda s:s.get('gt',-1)))}{LF}"
            )
