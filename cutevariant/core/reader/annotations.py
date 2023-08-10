from typing import List
import polars as pl


def extract_annotations(
    vcf_lf: pl.LazyFrame, info_props: dict, selected_fieds: List[str]
) -> pl.LazyFrame:
    """From VCF LazyFrame, extract selected info fields. If no selected_fields is empty, select all fields"""

    expressions = []

    for info_prop in info_props:
        if not selected_fieds or info_prop["id"].lower() in selected_fieds:
            regex = rf"{info_prop['id']}=([^;]+);?"

            local_expr = pl.col("info").str.extract(regex, 1)

            if info_prop["number"] == "1":
                if info_prop["type"] == "Integer":
                    local_expr = local_expr.cast(pl.Int64)
                elif info_prop["type"] == "Float":
                    local_expr = local_expr.cast(pl.Float64)
                elif info_prop["type"] in {"String", "Character"}:
                    pass  # Not do anything on string or character
                else:
                    pass  # Not reachable

            else:
                local_expr = local_expr.str.split(",")
                if info_prop["type"] == "Integer":
                    local_expr = local_expr.cast(pl.List(pl.Int64))
                elif info_prop["type"] == "Float":
                    local_expr = local_expr.cast(pl.List(pl.Float64))
                elif info_prop["type"] in {"String", "Character"}:
                    pass  # Not do anything on string or character
                else:
                    pass  # Not reachable

            expressions.append(local_expr.alias(info_prop["id"].lower()))

    return vcf_lf.with_columns(expressions).select(pl.exclude("info"))
