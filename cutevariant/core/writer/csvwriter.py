from cutevariant.core import command
from .abstractwriter import AbstractWriter
import csv


class CsvWriter(AbstractWriter):
    """Writer allowing to export variants of a project into a CSV file.

    Attributes:
        device: a file object typically returned by open("w")

    Example:
        with open(filename,"rw") as file:
            writer = MyWriter(file)
            writer.save(conn)
    """

    def __init__(self, device):
        super(AbstractWriter, self).__init__()
        super().__init__(device)

    def save(self, conn, delimiter="\t", **kwargs) -> bool:
        """Dump variants into CSV file

        .. TODO:: move SQL query into a dedicated place

        Args:
            delimiter (str, optional): Delimiter char used in exported file;
                (default: "\t").
            **kwargs (dict, optional): Arguments can be given to override
                individual formatting parameters in the current dialect.
        """
        writer = csv.writer(self.device, delimiter=delimiter, **kwargs)
        g = (row.values() for row in command.execute(conn, "SELECT chr, pos, ref, alt FROM variants"))
        writer.writerows(g)
