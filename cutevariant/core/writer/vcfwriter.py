import vcf

from cutevariant.core import sql
from cutevariant.core import command as cmd
from cutevariant.core.writer import AbstractWriter

import json


class VcfWriter(AbstractWriter):
    """Writer allowing to export variants of a project into a VCF file.

    Attributes:

        device: a file object typically returned by open("w")

    Example:
        with open(filename,"rw") as file:
            writer = MyWriter(file)
            writer.save(conn)
    """

    VCF_TYPE = {"int": "Integer", "float": "Float", "str": "String"}

    # TEMPORARY BECAUSE CUTEVARIANT MUST STORE PHASE GENOTYPE
    GENOTYPE_MAP = {None: "./.", "": "./.", -1: "./.", 0: "0/0", 1: "0/1", 2: "1/1"}

    def __init__(
        self,
        conn,
        filename,
        fields=["chr", "pos", "ref", "alt"],
        source="variants",
        filters={},
    ):
        super().__init__(conn, filename, fields, source, filters)

    def write_header(self, device):

        # export header

        for key, value in sql.get_metadatas(self.conn).items():
            device.write(f"##{key}={value}\n")

        # save infos
        self.info_fields = [
            info_field
            for info_field in sql.get_field_by_category(self.conn, "variants")
            if info_field["name"] in self.fields
            # Only keep info if they have been asked for by the user
        ] + [
            info_field
            for info_field in sql.get_field_by_category(self.conn, "annotations")
            if info_field["name"] in self.fields
            # Only keep info if they have been asked for by the user
        ]

        # INFO fields
        for field in self.info_fields:

            name = field["name"]
            # These fields will be created when cutevariant loads the VCF back in
            if name in (
                "favorite",
                "classification",
                "tags",
                "comment",
                "count_hom",
                "count_het",
            ):
                continue

            descr = field["description"]
            vcf_type = VcfWriter.VCF_TYPE.get(field["type"], "String")

            device.write(
                f'##INFO=<ID={name}, Number=1, Type={vcf_type}, Description="{descr}">\n',
            )

        # FORMAT fields
        for field in sql.get_field_by_category(self.conn, "samples"):

            name = field["name"]
            # These fields will be created when cutevariant loads the VCF back in
            if name in (
                "classification",
                "tags",
                "comment",
            ):
                continue

            descr = field["description"]
            vcf_type = VcfWriter.VCF_TYPE.get(field["type"], "String")

            device.write(
                f'##FORMAT=<ID={name}, Number=1, Type={vcf_type}, Description="{descr}">\n'
            )

    def get_info_column(self, variant: dict, fields=None):
        """
        Returns
        """
        if not fields:
            fields = []

        return (
            ";".join(
                [
                    f"{info_field['name']}={variant[info_field['name']]}"
                    for info_field in self.info_fields  # Only export allowed info fields (self.info_fields has been filtered)
                    if info_field["name"] in fields
                    and info_field["name"]
                    not in (
                        "favorite",
                        "classification",
                        "tags",
                        "comment",
                        "count_hom",
                        "count_het",
                    )
                ]
            )
            or "."
        )

    def get_format_column(self, variant_id: int):
        """
        Returns the fields that describe the samples for this variant, separated by :
        """
        return "GT"

    def get_samples_column(self, variant_id: int, fields=None):
        ssample = []
        sample_annotations = sql.get_genotypes(self.conn, variant_id, fields=fields)

        for annotations in sample_annotations:
            sssample = []
            for ann in annotations:
                if ann in fields:
                    if ann == "gt":
                        # ssample.append(VcfWriter.GENOTYPE_MAP[ann.get("gt", "")])
                        sssample.append(self.GENOTYPE_MAP[annotations.get("gt", "./.")])
                    else:
                        if annotations[ann] == None:
                            sssample.append(".")
                        else:
                            sssample.append(str(annotations[ann]))
            ssample.append(":".join(sssample))

        return "\t".join(ssample)

    def async_save(self, *args, **kwargs):

        self.fields = list(
            filter(
                lambda name: name
                not in {
                    "chr",
                    "pos",
                    "rsid",
                    "ref",
                    "alt",
                    "qual",
                },  # These names are reserved and should not appear in the user-specific fields
                self.fields,
            )
        )

        device = open(self.filename, "w")
        # Write the header (metadata) of the VCF
        self.write_header(device)

        # Write the header (column labels) of the VCF
        samples = sql.get_samples(self.conn)
        samples_name = "\t".join([item["name"] for item in samples])
        device.write(
            f"#CHROM  POS     ID      REF     ALT     QUAL    FILTER  INFO    FORMAT  {samples_name}\n"
        )

        # Out of all the fields asked by the user, ignore those that are mandatory for the VCF
        custom_fields = list(
            filter(
                lambda name: name.lower() not in {"chr", "pos", "rsid", "ref", "alt", "qual"},
                self.fields,
            )
        )

        # FORMAT fields
        format_fields = []
        for format_field in dict(
            self.conn.execute(f"""SELECT * FROM genotypes LIMIT 1""").fetchone()
        ):
            if format_field not in (
                "variant_id",
                "sample_id",
                "name",
                "valid",
                "classification",
                "tags",
                "comment",
            ):
                format_fields.append(format_field)

        # Start the actual variant writing loop
        for index, variant in enumerate(
            cmd.select_cmd(
                self.conn,
                ["chr", "pos", "rsid", "ref", "alt", "qual"] + custom_fields,
                self.source,
                filters=self.filters,
                limit=None,
            )
        ):

            # When entering this loop, you can have the same variant id twice
            chrom = variant["chr"]
            pos = variant["pos"]
            rsid = variant["rsid"]
            ref = variant["ref"]
            alt = variant["alt"]
            qual = variant["qual"]
            ffilter = "PASS"

            info = self.get_info_column(variant, custom_fields)
            # fformat = self.get_format_column(variant)
            fformat = ":".join(format_fields)
            # ssample = self.get_samples_column(variant_id=variant["id"], fields=["gt","vaf"])
            ssample = self.get_samples_column(variant_id=variant["id"], fields=format_fields)

            device.write(
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
                        ssample,
                    )
                )
                + "\n"
            )

            yield index

        device.close()


if __name__ == "__main__":

    import tests.utils as utils
    import sqlite3

    conn = utils.create_conn(
        "/home/charles/Documents/Stage Cutevariant/Exercice 2/chr7_three_variants.vcf",  # Your file name here
        "snpeff",
    )

    writer = VcfWriter(conn, "test_x.vcf")
    writer.save()
