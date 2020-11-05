import csv

from .abstractwriter import AbstractWriter
from cutevariant.core.sql import get_samples


class PedWriter(AbstractWriter):
    """Writer allowing to export samples of a project into a PED/PLINK file.

    Attributes:

        device: a file object typically returned by open("w")

    Example:
        >>> with open(filename,"rw") as file:
        ...    writer = MyWriter(file)
        ...    writer.save(conn)
    """

    def __init__(self, device):
        super().__init__(device)

    def save(self, conn, delimiter="\t", **kwargs):
        r"""Dump samples into a tabular file

        Notes:
            File is written without header.

        Example of line::

            `family_id\tindividual_id\tfather_id\tmother_id\tsex\tphenotype`

        Args:
            conn (sqlite.connection): sqlite connection
            delimiter (str, optional): Delimiter char used in exported file;
                (default: ``\t``).
            **kwargs (dict, optional): Arguments can be given to override
                individual formatting parameters in the current dialect.
        """
        writer = csv.DictWriter(
            self.device,
            delimiter=delimiter,
            lineterminator="\n",
            fieldnames=["family_id", "name", "father_id", "mother_id", "sex", "phenotype"],
            extrasaction="ignore",
            **kwargs
        )
        g = list(get_samples(conn))
        # Map DB ids with individual_ids
        individual_ids_mapping = {sample["id"]: sample["name"] for sample in g}
        # Add default value
        individual_ids_mapping[0] = 0
        # Replace DB ids
        for sample in g:
            sample["father_id"] = individual_ids_mapping[sample["father_id"]]
            sample["mother_id"] = individual_ids_mapping[sample["mother_id"]]
        writer.writerows(g)

    def save_from_list(self, samples, delimiter="\t", **kwargs):
        r"""Dump samples into a tabular file

        Args:
            samples(list): Iterable of samples; each sample is a list itself.
                => It's up to the user to give field in the correct order.
            delimiter (str, optional): Delimiter char used in exported file;
                (default: ``\t``).
            **kwargs (dict, optional): Arguments can be given to override
                individual formatting parameters in the current dialect.

        Notes:
            Replace None or empty strings to 0 (unknown PED ID)
        """
        writer = csv.writer(
            self.device, delimiter=delimiter, lineterminator="\n", **kwargs
        )
        # Replace None or empty strings to 0 (unknown PED ID)
        clean_samples = ([item if item else 0 for item in sample] for sample in samples)
        writer.writerows(clean_samples)
