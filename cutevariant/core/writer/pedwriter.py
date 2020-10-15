import csv

from .abstractwriter import AbstractWriter
from cutevariant.core.sql import get_samples


class PedWriter(AbstractWriter):
    """Writer allowing to export samples of a project into a PED/PLINK file.

    Attributes:

        device: a file object typically returned by open("w")

    Example:

        with open(filename,"rw") as file:
            writer = MyWriter(file)
            writer.save(conn)
    """

    def __init__(self, device):
        super().__init__(device)

    def save(self, conn, delimiter="\t", **kwargs) -> bool:
        r"""Dump samples into a tabular file

        Notes:
            File is written without header.

        Example of line:

            `family_id\tindividual_id\tfather_id\tmother_id\tsex\tphenotype`

        Args:

            delimiter (str, optional): Delimiter char used in exported file;
                (default: "\t").
            **kwargs (dict, optional): Arguments can be given to override
                individual formatting parameters in the current dialect.
        """
        writer = csv.DictWriter(
            self.device,
            delimiter=delimiter,
            lineterminator="\n",
            fieldnames=["name", "fam", "father_id", "mother_id", "sex", "phenotype"],
            extrasaction="ignore",
            **kwargs
        )
        g = (
            dict(row) for row in get_samples(conn)
        )
        writer.writerows(g)
