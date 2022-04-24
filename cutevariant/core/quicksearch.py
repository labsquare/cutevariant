from typing import Tuple
import re

from cutevariant import LOGGER

from .vql import VQLSyntaxError, parse_one_vql

# Needs configurables:

# - gene column name
# - TODO allow partial match for gene name (could be great for ABC genes, i.e. look for ABC* genes)


def quicksearch(query: str) -> dict:
    """Returns a VQL query from a query string

    Args:
        query (str): String to search for, in any form. Currently, three possibilities:
            - CFTR,GJB2,... just a gene name
            - chr7:117120017-117308718 (genomic coordinates)
            - ann.gene="CFTR" OR pos > 42

    Returns:
        dict: appropriate filter corresponding to the query string
    """
    strategies = [parse_gene_query, parse_coords_query, parse_vql_query]
    for strat in strategies:
        success, parsed = strat(query)
        if success:
            return parsed
    return dict()


def parse_gene_query(query: str) -> Tuple[bool, dict]:
    """Parse quick search text. This function is the gene strategy.

    Args:
        query (str): A quick search query, presumably for a gene

    Returns:
        Tuple[bool,dict]: True if the query string looks like a gene, as well as the corresponding filter dict
    """
    if not query:
        return False, ""

    match = re.findall(r"^(\w+)$", query)

    if match:
        gene_name = match[0]

        gene_col_name = "gene"

        return True, {"$and": [{f"ann.{gene_col_name}": gene_name}]}
    else:
        return False, dict()


def parse_coords_query(query: str) -> Tuple[bool, dict]:
    """Parse quick search text. This function is the genomic location strategy.

    Args:
        query (str): A quick search query, presumably for locus coordinates

    Returns:
        Tuple[bool,dict]: True if the query string is in the form 'chr7:117120017-117308718', as well as the corresponding filter dict
    """
    if not query:
        return False, ""

    match = re.findall(r"(\w+):(\d+)-(\d+)", query)

    if match:
        chrom, start, end = match[0]
        start = int(start)
        end = int(end)

        # Don't create a filter, to avoid confusion
        if end < start:
            return False, dict()
        return True, {
            "$and": [{"chr": chrom}, {"pos": {"$gte": start}}, {"pos": {"$lte": end}}]
        }
    else:
        return False, dict()


def parse_vql_query(query: str) -> Tuple[bool, dict]:
    """Parse quick search text. This function is the vql filter strategy, aka the fallback one, if all the others fail

    Args:
        query (str): A quick search query, presumably for a gene

    Returns:
        Tuple[bool,dict]: True if the query string looks like a VQL filter statement, as well as the corresponding filter dict
    """
    if not query:
        return False, ""

    res = None

    try:
        res = parse_one_vql(f"SELECT chr,pos FROM variants WHERE {query}")
    except VQLSyntaxError as e:
        LOGGER.error("Invalid VQL filter", e.args[0])

    if res:
        return True, res["filters"]
    else:
        return False, dict()
