# Standard imports
import csv

# Custom imports
from .abstractwriter import AbstractWriter
from cutevariant.core import command as cmd
import cutevariant.commons as cm


LOGGER = cm.logger()


class BedWriter(AbstractWriter):
    """Writer allowing to export variants of a project into a CSV file.

    Attributes:

        device: a file object typically returned by open("w")

    Example:
        >>> with open(filename,"rw") as file:
        ...    writer = MyWriter(file)
        ...    writer.save(conn)
    """

    def __init__(self, conn, device):
        super().__init__(conn, device)

    def total_count(self):
        """
        Returns the total count of elements we will have to write.
        Should be called everytime the fields get updated
        """
        self.variant_count = cmd.count_cmd(
            self.conn, fields=self.fields, filters=self.filters
        )["count"]
        return self.variant_count

    def async_save(self, *args, **kwargs):
        r"""Iteratively dumps variants into CSV file
        This function creates a generator that yields progress

        Examples::

            chr pos     ref alt
            11  10000   G   T
            11  120000  G   T

        Args:
            **kwargs (dict, optional): Arguments can be given to override
                individual formatting parameters in the current dialect.
            Examples of useful kwargs:
                delimiter : How the fields are separated in the CSV file
                lineterminator : How the lines end in the CSV file
        """

        variant_request_args = {
            "fields": ["chr", "pos"],
            "source": "variants",
            "limit": None,
        }

        total_count = self.total_count()

        for progress, variant in enumerate(
            cmd.select_cmd(self.conn, **variant_request_args), start=1
        ):

            chrom = str(variant["chr"])
            start = str(variant["pos"])
            name = str("test")
            end = str(variant["pos"] + 1)

            line = "\t".join([chrom, start, end, name]) + "\n"

            self.device.write(line)

            yield progress, total_count

        #     chrom = variant["chr"]
        #     start = variant["pos"]
        #     end = start + 1

        #     device.write("\t".join([chrom, start, end]) + "\n")

        #     yield progress, self.variant_count
