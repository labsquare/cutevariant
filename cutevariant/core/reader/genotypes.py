from typing import Callable, Sequence, List
import polars as pl
import re
from IPython import embed


class NoGenotypeError(Exception):
    pass


def __format_gt(expr: pl.Expr, /, name: str) -> pl.Expr:
    """Manage gt field."""
    # 1/2 -> 1
    # 2/2 -> 2
    return expr.str.count_match("1").cast(pl.UInt8).alias(name.lower())


def __format_one_float(expr: pl.Expr, /, name: str) -> pl.Expr:
    return expr.apply(lambda s: float(s)).cast(pl.Float32)


def __format_one_int(expr: pl.Expr, /, name: str) -> pl.Expr:
    """Manage integer field."""
    return expr.str.parse_int(10, strict=False).cast(pl.UInt16).alias(name.lower())


def __format_one_str(expr: pl.Expr, /, name: str) -> pl.Expr:
    """Manage string field."""
    return expr.alias(name.lower())


def __format_list_int(expr: pl.Expr, /, name: str) -> pl.Expr:
    """Manage list of integer field."""
    return (
        expr.str.split(",")
        .list.eval(pl.element().str.parse_int(10, strict=False).cast(pl.UInt16))
        .alias(name.lower())
    )


def __format_list_float(expr: pl.Expr, /, name: str) -> pl.Expr:
    return expr.str.split(",").list.eval(pl.element().apply(lambda s: float(s)).cast(pl.Float32))


def __format_list_str(expr: pl.Expr, /, name: str) -> pl.Expr:
    """Manag list string field."""
    return expr.str.split(",").alias(name.lower())


def format2expr(
    format_info: dict,
) -> dict[str, Callable[[pl.Expr, str], pl.Expr]]:
    """
    Read vcf header to generate a list of expressions to extract genotypes information.
    """

    expressions: dict[str, Callable[[pl.Expr, str], pl.Expr]] = {}

    for info in format_info:
        name = info["id"]
        number = info["number"]
        format_type = info["type"]

        if name == "GT":
            expressions["GT"] = __format_gt
            continue

        if number == "1":
            if format_type == "Integer":
                expressions[name] = __format_one_int
            elif format_type == "Float":
                expressions[name] = __format_one_float
            elif format_type in {"String", "Character"}:
                expressions[name] = __format_one_str
            else:
                pass  # Not reachable

        else:
            if format_type == "Integer":
                expressions[name] = __format_list_int
            elif format_type == "Float":
                expressions[name] = __format_list_float
            elif format_type in {"String", "Character"}:
                expressions[name] = __format_list_str
            else:
                pass  # Not reachable

    return expressions


def genotypes(
    vcf_lf: pl.LazyFrame,
    col2expr: dict[str, Callable[[pl.Expr, str], pl.Expr]],
) -> pl.LazyFrame:
    """Extract genotypes information of raw VCF LazyFrame

    Only line with format value match `format_str` are considered.

    """
    if "format" not in vcf_lf.columns:
        raise NoGenotypeError

    format_str: str = vcf_lf.select(pl.col("format").first().cast(pl.Utf8)).collect().item()

    vcf_lf = vcf_lf.select([*vcf_lf.columns[vcf_lf.columns.index("format") :]])

    # Clean bad variant
    vcf_lf = vcf_lf.filter(pl.col("format").str.starts_with(format_str)).select(*vcf_lf.columns[1:])

    # Found index of genotype value
    col_index = {
        key: index
        for (index, key) in enumerate(
            format_str.split(":"),
        )
    }

    # Pivot value

    genotypes = vcf_lf.melt(id_vars=["id"]).with_columns(
        [
            pl.col("id"),
            pl.col("variable").alias("sample"),
            pl.col("value").str.split(":"),
        ],
    )

    # Split genotype column in sub value
    genotypes = genotypes.with_columns(
        [pl.col("value").list.get(index).pipe(function=col2expr[col], name=col) for col, index in col_index.items()],  # type: ignore # noqa: PGH003
    )

    # Select intrusting column
    genotypes = genotypes.select(["id", "sample", *[col.lower() for col in col_index]])

    return genotypes
