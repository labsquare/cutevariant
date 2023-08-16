import os
from typing import Sequence, List
import typing
import polars as pl
import duckdb as db

import gzip

import re

from annotations import extract_annotations
from quality import extract_quality
from genotypes import format2expr, genotypes

from IPython import embed

from cutevariant.core.reader.abstractreader import AbstractReader

from IPython import embed


class VcfReader(AbstractReader):
    def __init__(self, filename: str) -> None:
        super().__init__(filename)
        self.vcf_cols = self.read_vcf_columns()

    def samples(self) -> typing.List[str]:
        return self.read_vcf_columns()[8:]

    def genotypes(self,format_fields:List[str]=None) -> pl.LazyFrame:
        lf_vcf = pl.scan_csv(
            self.filename,
            separator="\t",
            comment_char="#",
            has_header=False,
            new_columns=self.vcf_cols,
        )
        lf_vcf = lf_vcf.with_columns(index_vcf_expr())

        column_props = self.parse_vcf_header()
        # Extract genotypes and other sample-related fields
        format_expr = format2expr(column_props["format"])
        if not format_fields:
            format_fields = [f["id"] for f in column_props["format"]]
        format_fields = [f.lower() for f in format_fields]

        genotypes_lf = genotypes(lf_vcf, format_expr)

        return genotypes_lf

    def variants(self) -> pl.LazyFrame:
        # Get raw vcf lazyframe
        lf_vcf = pl.scan_csv(
            self.filename,
            separator="\t",
            comment_char="#",
            has_header=False,
            new_columns=self.vcf_cols,
        )
        # Extract variants and select columns
        lf_vcf = lf_vcf.with_columns(index_vcf_expr())
        return lf_vcf.select(["chrom", "pos", "ref", "alt"])

    def is_gzipped(self):
        with open(self.filename, "rb") as f:
            if f.read(2) == b"\x1f\x8b":
                return True

    def file_reader(self):
        """
        Simple file reader that yields one line at a time, no matter what the file type.
        Raises an error if filename does not exist
        """
        if not os.path.isfile(self.filename):
            raise FileNotFoundError(self.filename)

        if self.is_gzipped(self.filename):
            with gzip.open(self.filename, "rt") as z:
                yield from z

        else:
            with open(self.filename, "rt") as f:
                yield from f

    def parse_vcf_header(self) -> dict:
        """
        Parses the VCF header of filename.
        """

        info_fields = []
        format_fields = []
        field_regex = re.compile(
            r"ID=(?P<id>[A-Za-z_][0-9A-Za-z_.]*),Number=(?P<number>[ARG0-9.]+),Type=(?P<type>Integer|Float|String|Character)"
        )

        for line in self.file_reader():
            line = line.rstrip()
            if line.startswith("##INFO="):
                info_match = field_regex.search(line)
                if info_match:
                    info_fields.append(info_match.groupdict())
            elif line.startswith("##FORMAT="):
                format_match = field_regex.search(line)
                if format_match:
                    format_fields.append(format_match.groupdict())
            elif line.startswith("#CHROM"):
                break
            else:
                pass

        return {
            "info": info_fields,
            "format": format_fields,
        }

    def read_vcf_columns(self) -> List[str]:
        """Reads vcf columns into a list
        >>> from cutevariant.core.reader import vcfreader
        >>> vcfreader.read_vcf_columns("examples/snpeff3.vcf")
        ['chrom', 'pos', 'rsid', 'ref', 'alt', 'qual', 'filter', 'info', 'format', 'isdbm322015', 'isdbm322016', 'isdbm322017', 'isdbm322018']
        """

        for line in self.file_reader():
            if line.startswith("#CHROM"):
                return line.replace("#", "").replace("ID", "RSID").lower().rstrip().split("\t")

    def import_vcf(
        self,
        output_dir: str,
        quality_fields: Sequence[str] = None,
        annotation_fields: Sequence[str] = None,
        format_fields: Sequence[str] = None,
        run_name: str = None,
    ):
        """Imports a new VCF (`filename`) into the project folder `output_dir`.
        This will create a new subfolder called `run_name` with four parquet files: `samples.parquet`, `variants.parquet`, `annotations.parquet`, and `quality.parquet`

        Args:
            filename (str): Name of a VCF file to import into project in `output_dir`
            output_dir (str): A folder initialized as a cutevariant project
            quality_fields (Sequence[str], optional): Quality fields to import. If set to None, all of them are imported. Defaults to None.
            annotation_fields (Sequence[str], optional): List of annotation fields to import. If set to None, all of them are imported. Defaults to None.
            format_fields (Sequence[str], optional): List of sample-specific information to import. If set to None, all of them are imported. Defaults to None.
            run_name (str, optional): Name of the subfolder to create inside the cutevariant project folder. If set to None, the subfolder is named `basename(dirname(filename))_basename(filename)`. Defaults to None.
        """

        vcf_cols = self.read_vcf_columns()

        # Get raw vcf lazyframe
        lf_vcf = pl.scan_csv(
            self.filename, separator="\t", comment_char="#", has_header=False, new_columns=vcf_cols
        )
        # Add index column (id)
        lf_vcf = lf_vcf.with_columns(index_vcf_expr())

        column_props = self.parse_vcf_header()

        # Extract variants and select columns
        variants_lf = lf_vcf.select(["id", "chrom", "pos", "ref", "alt"])

        if not annotation_fields:
            annotation_fields = [f["id"] for f in column_props["info"]]
        annotation_fields = [f.lower() for f in annotation_fields]

        # Extract annotations and select columns
        annotations_lf = extract_annotations(
            lf_vcf, column_props["info"], annotation_fields
        ).select(["id", *annotation_fields])

        # Extract quality info columns
        quality_lf = extract_quality(lf_vcf, column_props["info"], quality_fields)

        # Prepare to write all parquet files from import
        os.makedirs(os.path.join(output_dir, run_name), exist_ok=True)

        variants_lf.sink_parquet(os.path.join(output_dir, run_name, "variants.parquet"))
        annotations_lf.sink_parquet(os.path.join(output_dir, run_name, "annotations.parquet"))
        quality_lf.sink_parquet(os.path.join(output_dir, run_name, "quality.parquet"))


def index_vcf_expr() -> pl.Expr:
    return (
        pl.concat_str(
            [pl.col("chrom"), pl.lit("-"), pl.col("pos"), pl.lit("-"), pl.col("ref"), pl.col("alt")]
        )
        .hash()
        .alias("id")
    )


if __name__ == "__main__":
    reader = VcfReader("/home/charles/Bioinfo/test.vcf")
