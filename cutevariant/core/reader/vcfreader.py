from functools import partial
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
    def __init__(self, filename: str, run_name: str) -> None:
        super().__init__(filename)
        self.run_name = run_name
        self.vcf_cols = self.read_vcf_columns()

    def samples(self) -> typing.List[str]:
        return self.vcf_cols[self.vcf_cols.index("format") + 1 :]

    def get_sample_fields(self, struct: dict, sample_name: str):
        return {
            field.lower(): value
            for field, value in zip(struct["format"].split(":"), struct[sample_name].split(":"))
        }

    def genotypes(self, samplename: str, method="fast") -> pl.LazyFrame:
        lf_vcf = pl.scan_csv(
            self.filename,
            separator="\t",
            comment_char="#",
            has_header=False,
            new_columns=self.vcf_cols,
        )
        # TODO: Benchmark
        if method == "slow":
            # Add variant ID
            # Looking for genotype information, select format field
            # Do that weird concat string to get columns joined and then split again to a dict
            # At the end, add the run name to the whole genotype information
            lf_vcf = (
                lf_vcf.with_columns(index_vcf_expr())
                .select(["format", samplename])
                .with_columns(
                    pl.concat_str([pl.col("format"), pl.lit("-"), pl.col(samplename)])
                    .alias("sample_fields")
                    .apply(
                        lambda s: {
                            f.lower(): v
                            for f, v in zip(s.split("-")[0].split(":"), s.split("-")[1].split(":"))
                        }
                    )
                )
                .unnest("sample_fields")
                .with_columns(pl.lit(self.run_name).alias("run_name"))
            )
        else:
            sample_fields_extractor = partial(self.get_sample_fields, sample_name=samplename)
            lf_vcf = (
                lf_vcf.with_columns(
                    pl.struct(["format", samplename]).apply(sample_fields_extractor)
                )
                .unnest("format")
                .with_columns(pl.lit(self.run_name).alias("run_name"))
            )

        return lf_vcf

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
        lf_vcf = lf_vcf.select(["chrom", "pos", "ref", "alt"]).with_columns(
            [index_vcf_expr(), pl.lit(self.run_name).alias("run_name")]
        )
        return lf_vcf

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

        if self.is_gzipped():
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

    def import_vcf(self, output_dir: str, auto_merge: bool = True):
        """Imports VCF specified in filename.

        Args:
            output_dir (str): Path to the cutevariant project directory to import VCF into
        """

        # Import variants
        variants_lf = self.variants()
        variants_filename = os.path.join(output_dir, "variants.parquet")
        if os.path.exists(variants_filename):
            if auto_merge:
                pl.concat(
                    [pl.scan_parquet(variants_filename), variants_lf]
                ).collect().write_parquet(variants_filename + ".new")
                os.rename(variants_filename + ".new", variants_filename)
        else:
            variants_lf.collect().write_parquet(variants_filename)

        # Import every sample in a different file
        for sample in self.samples():
            genotype_lf = self.genotypes(sample)
            sample_filename = os.path.join(output_dir, "samples", f"{sample}.parquet")
            if os.path.exists(sample_filename):
                pl.concat([pl.scan_parquet(sample_filename), genotype_lf]).collect().write_parquet(
                    sample_filename + ".new"
                )
                os.rename(sample_filename + ".new", sample_filename)
            else:
                genotype_lf.collect().write_parquet(sample_filename)


def index_vcf_expr() -> pl.Expr:
    return (
        pl.concat_str(
            [
                pl.col("chrom"),
                pl.lit("-"),
                pl.col("pos"),
                pl.lit("-"),
                pl.col("ref"),
                pl.lit("-"),
                pl.col("alt"),
            ]
        )
        .hash()
        .alias("id")
    )


if __name__ == "__main__":
    reader = VcfReader("examples/example.vcf", "RUN_TEST")
    reader.import_vcf("/home/charles/Bioinfo/tests_cutevariants/premier_projet")
