"""Module to handle BED files"""
# Standard imports
import pybedtools

# Custom imports
from cutevariant.commons import logger

LOGGER = logger()


def parse_bed_file(filepath):
    """Parse the given BED file with 'pybedtools' package, yield features in the file

    .. note:: chromosom field is processed to remove 'chr' prefixes.

    .. note:: Intervals yielded have the following attributes:
        interval.chrom, interval.start, interval.stop

        Other attributes are described here:
        https://daler.github.io/pybedtools/intervals.html

    We assume that the given BED file is composed of lines with the following fields:
        - chromosom
        - start position
        - end position

    .. seealso:: https://www.ensembl.org/info/website/upload/bed.html
    """
    bedtool = pybedtools.BedTool(filepath)
    if bedtool.count() == 0:
        LOGGER.error("parse_bed_file:: No interval detected in the given BED file!")
        raise ValueError("No interval detected in the given BED file!")

    for interval in bedtool:
        # Remove 'chr' prefix from the chromosome name
        interval.chrom = interval.chrom.replace("chr", "")

        yield interval

#    with open(filepath, "r") as f_d:
#        # Quick tests on the input file...
#        first_line = f_d.readline()
#        csv_dialect = csv.Sniffer().sniff(first_line)
#
#        # Build a csv reader
#        f_d.seek(0)
#        csv_reader = csv.DictReader(f_d, dialect=csv_dialect)
#
#        LOGGER.debug(
#            "CsvReader::init: CSV fields found: %s", csv_reader.fieldnames
#        )
#
#        for item in csv_reader:
#            print(item)


if __name__ == "__main__":

#    parse_bed_file("/media/DATA/Projets/cutevariant/cutevariant/examples/a.bed")
#    parse_bed_file("/media/DATA/Projets/cutevariant/cutevariant/examples/test_9_columns.bed")
    g = parse_bed_file("/media/DATA/Projets/cutevariant/cutevariant/examples/test.bed")

    tuple(g)
