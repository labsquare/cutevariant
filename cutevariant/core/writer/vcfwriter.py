import vcf

from .abstractwriter import AbstractWriter

import json


class VcfWriter(AbstractWriter):
    """Writer allowing to export variants of a project into a VCF file.

    Attributes:

        device: a file object typically returned by open("w")

    Example:
        >>> with open(filename,"rw") as file:
        ...    writer = MyWriter(file)
        ...    writer.save(conn)
    """

    def __init__(self, device, fields_to_export):
        super().__init__(device, fields_to_export)

    def async_save(self):
        raise NotImplementedError()



