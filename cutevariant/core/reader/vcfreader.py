from functools import partial
import os
from typing import Sequence, List, Tuple
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


class VcfReader(AbstractReader):
    def __init__(self, filename: str, run_name: str) -> None:
        super().__init__(filename)
        self.run_name = run_name
        self.vcf_cols = self.read_vcf_columns()
        self.vcf_fields = self.parse_vcf_header()

    def samples(self) -> typing.List[str]:
        return self.vcf_cols[self.vcf_cols.index("format") + 1 :]

    def genotypes(
        self, samplename: str, ploidy=2
    ) -> Tuple[pl.LazyFrame, pl.LazyFrame, pl.LazyFrame]:
        lf_vcf = pl.scan_csv(
            self.filename,
            separator="\t",
            comment_char="#",
            has_header=False,
            new_columns=self.vcf_cols,
        )

        # TODO: Try this instead: https://stackoverflow.com/questions/74521285/how-to-zip-2-list-columns-on-python-polars

        lf_vcf = (
            lf_vcf.with_columns(
                pl.concat_str([pl.col("ref"), pl.lit(","), pl.col("alt")])
                .str.split(",")
                .alias("refalt")
            )
            .with_columns([pl.col("alt").str.split(",")])
            .explode("alt")
            .with_columns(index_vcf_expr())
            .with_columns(
                [
                    pl.col("format").str.split(":"),
                    pl.col(samplename).str.split(":"),
                ]
            )
            .explode(["format", pl.col(samplename)])
        )

        # Get the GGT column: a list consisting of each parental genotype
        ggt_lf = (
            lf_vcf.filter(pl.col("format") == "GT")
            .with_columns(
                pl.col(samplename)
                .str.replace(r"[|]", "/")
                .str.split("/")
                .list.eval(pl.element().cast(pl.Int8))
            )
            .with_columns(
                pl.concat_list(
                    pl.col("refalt").list.get(pl.col(samplename).list.get(0)),
                    pl.col("refalt").list.get(pl.col(samplename).list.get(1)),
                ).alias(samplename)
            )
            .select(["id", "format", samplename])
            .filter(pl.col(samplename).list.lengths() != 1)
        )

        gt_lf = (
            lf_vcf.select(["id", "format", samplename])
            .filter(pl.col("format") == "GT")
            .with_columns(
                pl.col(samplename)
                .str.replace(r"[|]", "/")
                .str.split("/")
                .list.eval(pl.element().cast(pl.Int8))
            )
            .filter(pl.col(samplename).list.lengths() != 1)
        )

        other_format_lf = lf_vcf.select(["id", "format", samplename]).filter(
            pl.col("format") != "GT"
        )

        return ggt_lf, gt_lf, other_format_lf

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
        lf_vcf = (
            lf_vcf.select(["chrom", "pos", "ref", "alt"])
            .with_columns(pl.col("chrom"))
            .with_columns(pl.col("alt").str.split(","))
            .explode("alt")
            .with_columns([index_vcf_expr()])
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
            overwrite_parquet_file(
                pl.concat([pl.scan_parquet(variants_filename), variants_lf]), variants_filename
            )
        else:
            variants_lf.sink_parquet(
                variants_filename,
            )

        # Import every sample in a different file
        for sample in self.samples():
            # Format fields come in three main types: ggt (the genotype in full notation), gt (the genotype in 0/1 or 1/2 notation), and other fields.
            ggt, gt, other_formats = self.genotypes(sample)

            # region Get GGT (special) fields list

            ggt_sample_filename = os.path.join(output_dir, "samples", f"{sample}.ggt.parquet")
            if os.path.exists(ggt_sample_filename):
                # The path already exists: use overwrite function to safely write concatenated frames over the same file name.
                pl.concat([pl.read_parquet(ggt_sample_filename), ggt.collect()]).write_parquet(
                    ggt_sample_filename + ".new"
                )
                os.rename(ggt_sample_filename + ".new", ggt_sample_filename)
            else:
                ggt.collect().write_parquet(
                    ggt_sample_filename,
                )
            # endregion

            # region Get genotypes fields
            gt_sample_filename = os.path.join(output_dir, "samples", f"{sample}.gt.parquet")
            if os.path.exists(gt_sample_filename):
                # The path already exists: use overwrite function to safely write concatenated frames over the same file name.
                overwrite_parquet_file(
                    pl.concat([pl.scan_parquet(gt_sample_filename), gt]), gt_sample_filename
                )
            else:
                gt.sink_parquet(
                    gt_sample_filename,
                )
            # endregion

            # region Get other format fields
            other_formats_sample_filename = os.path.join(output_dir, "samples", f"{sample}.parquet")
            if os.path.exists(other_formats_sample_filename):
                # The path already exists: use overwrite function to safely write concatenated frames over the same file name.
                overwrite_parquet_file(
                    pl.concat([pl.scan_parquet(other_formats_sample_filename), other_formats]),
                    other_formats_sample_filename,
                )
            else:
                other_formats.sink_parquet(
                    other_formats_sample_filename,
                )
            # endregion


def overwrite_parquet_file(lazyframe: pl.LazyFrame, filename: str):
    lazyframe.sink_parquet(filename + ".new")
    os.rename(filename + ".new", filename)


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
    reader.import_vcf("/home/charles/Bioinfo/tests_cutevariant/premier_projet")
