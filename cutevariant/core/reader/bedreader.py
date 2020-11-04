"""Module to handle BED files"""
# Standard imports
import gzip
import csv
import os
import io
import re

# Custom imports
import cutevariant.commons as cm

LOGGER = cm.logger()


class BedReader:
    r"""BED file parser

    It is a substitution to pybedtools that is a (too) big black box to make lots
    of things, while we only need the file parser.
    Thus, pybedtools is not multiplatform compatible (thanks to Winshit OS).
    Thus (again), pybedtools doesn't support files with spaces as separators
    (while the specification is implicit about it)...

    We support:
        - Simple text files
        - BED data as string
        - Compressed gzip files
        - Tabs and spaces files
        - Bedgraph files
        - BED files with headers

    .. seealso:: BED specs: https://www.ensembl.org/info/website/upload/bed.html

    How to use::

        intervals = BedReader("myfile.bed.gz)
        generator = iter(intervals)
        first_interval = next(generator)

        intervals = BedReader("myfile.bed)

        large_string = \"""
            chr1 1    10   feature1  0 +
            chr1 50   60   feature2  0 -
            chr1 51 59 another_feature 0 +
        \"""
        intervals = BedReader(large_string)

        for interval in intervals:
            print(interval)
    """

    def __init__(self, filepath, *args, **kwargs):

        self.count = 0
        self.filepath = filepath

        # Autodetection of string and filepaths
        if not os.path.exists(self.filepath):
            self.is_from_string = True
            self.is_gz_file = False
        else:
            self.is_from_string = False
            self.is_gz_file = cm.is_gz_file(filepath)

    def __iter__(self):
        """Yield Interval objects in the given BED file

        Each Interval object is an OrderedDict with the following keys:
            - chrom
            - start
            - end
            - name
            - score
            - strand
            - thickStart
            - thickEnd
            - itemRgb
            - blockCount
            - blockSizes
            - blockStarts

        Excedent data is put in and additional column 'misc'.
        Empty columns contain None values.

        :return: Generator of Intervals
        :rtype: <generator <OrderectDict>>
        """
        if self.is_from_string:
            # Clean the string:
            # Remove spaces at the start and end
            # Remove duplicated spaces in the string

            self.filepath = re.sub(" +", " ", self.filepath.strip())
            self.filepath = re.sub("\n ", "\n", self.filepath.strip())

            # Load in memory file
            yield from self.get_intervals(io.StringIO(self.filepath))
        else:
            if self.is_gz_file:
                # Handle gzip file
                with gzip.open(self.filepath, "rt") as stream:
                    yield from self.get_intervals(stream)
            else:
                # Handle text file
                with open(self.filepath, "r") as stream:
                    yield from self.get_intervals(stream)

    def get_intervals(self, stream):
        """Yield Interval objects in the given stream

        .. seealso:: :meth:`__iter__`
        """
        # Throws line with headers
        skipped_header_line = 0  # Will be used to rewind the stream
        for line in stream:
            if (
                line.startswith(("@", "#", "track", "browser"))
                or not line.strip()
            ):
                # Header detected
                LOGGER.debug("comment: %s", line)
                skipped_header_line += 1
                continue
            break

        # Quick tests on the first line of data...
        # Delimiters can only be '\t' or ' ' since
        # 'itemRgb' column is comma separated.

        # Rewind the stream
        stream.seek(0)
        [next(stream) for _ in range(skipped_header_line)]
        try:
            # If there is no data at all or after the header
            data_line = next(stream)
        except StopIteration:
            LOGGER.debug("No interval detected in the given BED file!")
            return

        csv_dialect = csv.Sniffer().sniff(data_line, delimiters="\t ")

        # Rewind the stream
        stream.seek(0)
        [next(stream) for _ in range(skipped_header_line)]
        # Build a csv reader
        bed_fieldnames = (
            "chrom",
            "start",
            "end",
            "name",
            "score",
            "strand",
            "thickStart",
            "thickEnd",
            "itemRgb",
            "blockCount",
            "blockSizes",
            "blockStarts",
        )
        csv_reader = csv.DictReader(
            stream, fieldnames=bed_fieldnames, restkey="misc", dialect=csv_dialect
        )

        line_number = 0
        for line_number, interval in enumerate(csv_reader, 1):
            # print(interval)
            yield interval

        self.count = line_number


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
    bedtool = BedReader(filepath)

    for interval in bedtool:
        # Remove 'chr' prefix from the chromosome name
        # interval["chrom"] = interval["chrom"].replace("chr", "")

        yield interval
