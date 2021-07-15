# Standard imports
import csv

# Custom imports
from .abstractwriter import AbstractWriter
from cutevariant.core import command as cmd
import cutevariant.commons as cm


from cutevariant import LOGGER


class BedWriter(AbstractWriter):
    """Writer allowing to export variants of a project into a CSV file.

    Attributes:

        device: a file object typically returned by open("w")

    Example:
            with open(filename,"rw") as file:
                writer = MyWriter(file)
                writer.save(conn)
    """

    def __init__(
        self, conn, device, fields=["chr", "pos"], source="variants", filters={}
    ):
        super().__init__(conn, device, fields, source, filters)

    def async_save(self, *args, **kwargs):
        r""""""

        self.fields = ["chr", "pos"]
        for count, variant in enumerate(self.get_variants()):

            chrom = str(variant["chr"])
            start = str(variant["pos"])
            end = str(variant["pos"] + 1)

            line = "\t".join([chrom, start, end]) + "\n"

            self.device.write(line)

            yield count + 1
