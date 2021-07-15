# Standard imports
import csv

# Custom imports
from .abstractwriter import AbstractWriter
from cutevariant.core import command as cmd
import cutevariant.commons as cm

import time

from cutevariant import LOGGER


class CsvWriter(AbstractWriter):
    """Writer allowing to export variants of a project into a CSV file.

    Attributes:

        device: a file object typically returned by open("w")

    Example:
            with open(filename,"rw") as file:
                writer = MyWriter(file)
                writer.save(conn)
    """

    def __init__(
        self,
        conn,
        device,
        fields=["chr", "pos", "ref", "alt"],
        source="variants",
        filters={},
    ):
        super().__init__(conn, device, fields, source, filters)

        self.separator = "\t"

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

        # Use dictionnary to define proper arguments for the writer, beforehand, in one variable
        dict_writer_options = {
            "f": self.device,
            "delimiter": self.separator,
            "lineterminator": "\n",
        }
        dict_writer_options.update(kwargs)

        # Set fieldnames **after** updating with kwargs to make sure they are not provided by the method's call kwargs
        dict_writer_options["fieldnames"] = list(self.fields)

        writer = csv.DictWriter(**dict_writer_options)
        writer.writeheader()

        for count, variant in enumerate(self.get_variants()):

            written_var = {k: v for k, v in dict(variant).items() if k in self.fields}
            writer.writerow(written_var)
            # time.sleep(0.1) For demo purposes only. If the database is small, the progress bar won't show up !
            yield count
