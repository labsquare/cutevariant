# Standard imports
import csv

# Custom imports
from cutevariant.core.writer.abstractwriter import AbstractWriter
from cutevariant.core import command as cmd
import cutevariant.commons as cm

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

    def __init__(self, device, fields_to_export=None):
        super().__init__(device, fields_to_export)

    def async_save(self, conn, *args, **kwargs):
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
        }

        # If we know the variant count in advance, let's use it to report relative progress
        if "variant_count" in kwargs:
            variant_count = kwargs["variant_count"]
        else:
            # TODO: Move this request so that upon saving, counting and retrieving variants are done as separated steps
            variant_count = cmd.count_cmd(
                conn, fields=self.fields, filters=self.filters
            )["count"]

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
            cmd.select_cmd(conn, **variant_request_args)
        ):
            written_var = {
                k: v for k, v in dict(variant).items() if k in writer.fieldnames
            }
            writer.writerow(written_var)
            yield progress, variant_count
