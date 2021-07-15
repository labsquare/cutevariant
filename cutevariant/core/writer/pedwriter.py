# Standard imports
import csv

# Custom imports
from .abstractwriter import AbstractWriter
from cutevariant.core import command as cmd
from cutevariant.core import sql
import cutevariant.commons as cm


from cutevariant import LOGGER


class PedWriter(AbstractWriter):
    """Writer allowing to export variants of a project into a CSV file.

    Attributes:

        device: a file object typically returned by open("w")

    Example:
        with open(filename,"rw") as file:
            writer = MyWriter(file)
            writer.save(conn)
    """

    def __init__(self, conn, device):
        super().__init__(conn, device)

    def async_save(self, *args, **kwargs):

        samples = list(sql.get_samples(self.conn))
        sample_map = dict((sample["id"], sample["name"]) for sample in samples)

        for count, sample in enumerate(samples):

            fam = str(sample["family_id"])
            name = str(sample["name"])
            father = sample["father_id"]
            mother = sample["mother_id"]
            sex = str(sample["sex"])
            phenotype = str(sample["phenotype"])

            line = (
                "\t".join(
                    [
                        fam,
                        name,
                        sample_map.get(father, "0"),
                        sample_map.get(mother, "0"),
                        sex,
                        phenotype,
                    ]
                )
                + "\n"
            )
            self.device.write(line)

            yield count
