import os
from time import strftime
from pyvcf2parquet import convert_vcf

from pathlib import Path
import polars as pl

import duckdb as db
from datetime import datetime

import re


def get_vcf_metadata(vcf_file: Path):
    metadata = dict()
    with open(vcf_file, "r") as f:
        for line in f:
            if line.startswith("##INFO"):
                _info_metadata = re.match(
                    r"##INFO=<ID=(?P<id>.*),Number=(?P<number>.*),Type=(?P<type>.*),Description=\"(?P<description>.*)\">",
                    line,
                ).groupdict()
                if "info" not in metadata:
                    metadata["info"] = [_info_metadata]
                else:
                    metadata["info"].append(_info_metadata)
            if line.startswith("##FORMAT"):
                _format_metadata = re.match(
                    r"##FORMAT=<ID=(?P<id>.*),Number=(?P<number>.*),Type=(?P<type>.*),Description=\"(?P<description>.*)\">",
                    line,
                ).groupdict()
                if "format" not in metadata:
                    metadata["format"] = [_format_metadata]
                else:
                    metadata["format"].append(_format_metadata)
            if line.startswith("#"):
                break
    return metadata


def import_vcf(project_dir: Path, vcf_file: Path):

    initial_parquet = project_dir / "incoming.parquet"
    convert_vcf(vcf_file, initial_parquet)

    initial_lf = pl.scan_parquet(initial_parquet).with_columns(
        pl.concat_str(
            pl.col("chromosome").cast(pl.Utf8),
            pl.col("position").cast(pl.Utf8),
            pl.col("reference"),
            pl.col("alternate").list.get(0),
            separator=":",
        )
        .hash()
        .alias("variant_hash"),
    )
    sample_names = [
        s.replace("_GT", "").replace("format_", "")
        for s in initial_lf.columns
        if s.endswith("_GT") and s.startswith("format_")
    ]

    # Turn ref=A, alt=[C,CT,CTT], format_sample_GT='0/2' into:
    # three rows :
    # ref=A, alt=C, format_sample_GT='0'
    # ref=A, alt=CT, format_sample_GT='1'
    # ref=A, alt=CTT, format_sample_GT='0'
    # Turn ref=A, alt=[C,CT,CTT], format_sample_GT='1/2' into:
    # three rows :
    # ref=A, alt=C, format_sample_GT='0'
    # ref=A, alt=CT, format_sample_GT='1'
    # ref=A, alt=CTT, format_sample_GT='1'

    aggregate_parquet = project_dir / "aggregates" / "variants.parquet"

    # Update aggregates/variants.parquet
    if os.path.isfile(aggregate_parquet):
        aggregate_lf = pl.read_parquet(aggregate_parquet)

        agg: pl.LazyFrame = pl.concat(
            [initial_lf, aggregate_lf], how="diagonal_relaxed"
        )

        agg = agg.with_columns(
            pl.col("hom_count").fill_null(0), pl.col("het_count").fill_null(0)
        )

    for sample in sample_names:
        sample_lf = initial_lf.select(
            pl.col("variant_hash"),
            pl.col(f"^format_{sample}_(.+)$").name.map(
                lambda s: s.replace(f"format_{sample}_", "")
            ),
        )
