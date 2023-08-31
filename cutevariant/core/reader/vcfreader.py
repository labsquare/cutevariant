from functools import partial
import os
from typing import Sequence, List, Tuple
import typing
import polars as pl
import duckdb as db

import gzip

import re

from polars import NoDataError

from annotations import extract_annotations
from quality import extract_quality
from genotypes import format2expr, genotypes

from IPython import embed

from cutevariant.core.reader.abstractreader import AbstractReader

from typing import NamedTuple


class SearchReplace(NamedTuple):
    Search: str
    Replace: str


class VcfReader(AbstractReader):
    def __init__(self, filename: str, run_name: str, sample_trim: SearchReplace = None) -> None:
        super().__init__(filename)
        self.run_name = run_name
        self.vcf_cols = self.read_vcf_columns()
        self.vcf_fields = self.parse_vcf_header()
        self._samples = self.vcf_cols[self.vcf_cols.index("format") + 1 :]
        if sample_trim:
            self.sample_trim(sample_trim)

    def sample_trim(self, sample_trim: SearchReplace):
        self._samples = [re.sub(sample_trim.Search, sample_trim.Replace, s) for s in self._samples]
        self.vcf_cols = self.vcf_cols[: -len(self._samples)] + self._samples

    def samples(self) -> typing.List[str]:
        return self._samples

    def genotypes(self, samplename: str, column: str, column_type: str) -> pl.LazyFrame:
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
            .select(["chrom", "pos", "refalt", "format", samplename])
            .with_columns(
                [
                    pl.col("format").str.split(":"),
                    pl.col(samplename).str.split(":"),
                ]
            )
            .explode(["format", pl.col(samplename)])
            .rename({"format": "field", samplename: "value"})
            .filter(pl.col("field") == column)
            .with_columns(index_vcf_expr())
            .with_columns(pl.lit(samplename).alias("samplename"))
            .with_columns(pl.lit(self.run_name).alias("runname"))
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
            raise_if_empty=False,
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

    def import_vcf(self, output_dir: str):
        """Imports VCF specified in filename.

        Args:
            output_dir (str): Path to the cutevariant project directory to import VCF into
        """

        # region Import variants
        try:
            variants_lf = self.variants()
        except NoDataError:
            return
        variants_filename = os.path.join(output_dir, "variants.parquet")
        if os.path.exists(variants_filename):
            overwrite_parquet_file(
                pl.concat([pl.scan_parquet(variants_filename), variants_lf]), variants_filename
            )
        else:
            variants_lf.sink_parquet(
                variants_filename,
            )
        # endregion

        # Import every sample in a different file
        for sample in self.samples():
            # Format fields come in three main types: ggt (the genotype in full notation), gt (the genotype in 0/1 or 1/2 notation), and other fields.
            format_fields = self.genotypes(sample)


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


def batch_import(input_folder: str, output_folder: str):
    """Imports VCFs in batch, assuming folder contains as many subfolders as there are run names"""
    for run_name in os.listdir(input_folder):
        if not os.path.isdir(os.path.join(input_folder, run_name)):
            continue
        for vcf in os.listdir(os.path.join(input_folder, run_name)):
            vcf_file_name = os.path.join(input_folder, run_name, vcf)
            if not os.path.isfile(vcf_file_name) or not vcf_file_name.endswith(".vcf"):
                continue
            reader = VcfReader(
                os.path.join(input_folder, run_name, vcf),
                run_name=run_name,
                # sample_trim=SearchReplace(r"_S\d+$", ""),
            )
            reader.import_vcf(output_folder)


if __name__ == "__main__":
    reader = VcfReader(
        "/media/charles/LINUXMINT/Documents/touslesppi/PPI070/1049-F_S74_extract.vcf",
        "PPI070",
        sample_trim=SearchReplace(r"_s\d+$", ""),
    )
    reader.import_vcf("/home/charles/Bioinfo/tests_cutevariant/premier_projet/")

# if __name__ == "__main__":
#     batch_import(
#         "/media/charles/SANDISK/TousLesVCF_PPI/touslesppi",
#         "/home/charles/Bioinfo/tests_cutevariant/tous_ppi",
#     )
