import csv

from .abstractwriter import AbstractWriter


class CsvWriter(AbstractWriter):
    """Writer allowing to export variants of a project into a CSV file.

    Attributes:

        device: a file object typically returned by open("w")

    Example:
        >>> with open(filename,"rw") as file:
        ...    writer = MyWriter(file)
        ...    writer.save(conn)
    """

    def __init__(self, device):
        super().__init__(device)

    def save(self, conn, delimiter="\t", **kwargs) -> bool:
        r"""Dump variants into CSV file

        .. TODO:: move SQL query into a dedicated place

        Examples::

            chr pos     ref alt
            11  10000   G   T
            11  120000  G   T

        Args:

            delimiter (str, optional): Delimiter char used in exported file;
                (default: ``\t``).
            **kwargs (dict, optional): Arguments can be given to override
                individual formatting parameters in the current dialect.
        """
        writer = csv.DictWriter(
            self.device,
            delimiter=delimiter,
            lineterminator="\n",
            fieldnames=["chr", "pos", "ref", "alt"],
            **kwargs
        )
        writer.writeheader()
        g = (
            dict(row) for row in conn.execute("SELECT chr, pos, ref, alt FROM variants")
        )
        writer.writerows(g)
