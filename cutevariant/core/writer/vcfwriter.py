import vcf

from cutevariant.core import sql
from cutevariant.core import command as cmd
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

    VCF_TYPE = {"int": "Integer", "float": "Float", "str": "String"}

    def __init__(self, device, fields_to_export):
        super().__init__(device, fields_to_export)


    def async_save(self):

        # export header
        for key, value in sql.get_metadatas(self.conn).items():
            self.device.write(f"##{key}={value}")

        # save infos
        for field in sql.get_field_by_category(self.conn, "variants"):
            name = field["name"]
            descr = field["description"]
            vcf_type = VcfWriter.VCF_TYPE.get(field["type"], "String")

            self.device.write(
                f'##INFO=<ID={name}, Number=1, Type={vcf_type}, Description="{descr}"',
            )

        # save format
        for field in sql.get_field_by_category(self.conn, "samples"):
            name = field["name"]
            descr = field["description"]
            vcf_type = VcfWriter.VCF_TYPE.get(field["type"], "String")

            self.device.write(
                f'##FORMAT=<ID={name}, Number=1, Type={vcf_type}, Description="{descr}"\n'
            )

        # save header variants

        samples = "\t".join([item["name"] for item in sql.get_samples(self.conn)])

        self.device.write(
            f"#CHROM  POS     ID      REF     ALT     QUAL    FILTER  INFO    FORMAT  {samples}\n"
        )

        for index, variant in enumerate(
            cmd.execute(
                self.conn,
                "SELECT chr, pos, rsid, ref,alt, qual, sample['TUMOR'].gt,sample['NORMAL'].gt FROM variants",
            )
        ):

            chrom = variant["chr"]
            pos = variant["pos"]
            rsid = variant["rsid"]
            ref = variant["ref"]
            alt = variant["alt"]
            qual = variant["qual"]
            ffilter = "PASS"
            info = "TRUC=3;BLA=24"
            fformat = "GT"
            samples = "1/1"

            self.device.write(
                "\t".join(
                    (
                        str(chrom),
                        str(pos),
                        str(rsid),
                        ref,
                        alt,
                        str(qual),
                        ffilter,
                        info,
                        fformat,
                        samples,
                    )
                )
                + "\n"
            )

        yield 1, 1
