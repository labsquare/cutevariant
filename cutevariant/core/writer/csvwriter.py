# Standard imports
import csv

# Custom imports
from .abstractwriter import AbstractWriter
from cutevariant.core import command as cmd
import cutevariant.commons as cm

import time

LOGGER = cm.logger()


class CsvWriter(AbstractWriter):
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
            "fields": self.fields,
            "source": self.source,
            "filters": self.filters,
            "order_desc": self.order_desc,
            "order_by": self.order_by,
            "group_by": self.group_by,
            "having": self.having,
            "limit": None,
        }

        # Use dictionnary to define proper arguments for the writer, beforehand, in one variable
        dict_writer_args = {
            "f": self.device,
            "delimiter": "\t",
            "lineterminator": "\n",
        }
        dict_writer_args.update(kwargs)

        # Set fieldnames **after** updating with kwargs to make sure they are not provided by the method's call kwargs
        dict_writer_args["fieldnames"] = list(self.fields)

        writer = csv.DictWriter(**dict_writer_args)
        writer.writeheader()

        for progress, variant in enumerate(
            cmd.select_cmd(self.conn, **variant_request_args), start=1
        ):
            # written_var = {
            #     k: v
            #     for k, v in dict(variant).items()
            #     if any(
            #         k in fieldname for fieldname in writer.fieldnames
            #     )  # Weird workaround to include fields even with their table prefix
            #     for k in writer.fieldnames
            # }
            written_var = {k: v for k, v in dict(variant).items() if k in self.fields}
            writer.writerow(written_var)
            # time.sleep(0.1) For demo purposes only. If the database is small, the progress bar won't show up !
            yield progress, self.variant_count
