from .abstractreader import AbstractReader
import vcf


class VcfReader(AbstractReader):

    type_mapping = {
        "Float": "Float",
        "Integer": "Integer",
        "Flag": "Boolean",
        "String": "String",
    }

    def __init__(self, device):
        super(VcfReader, self).__init__(device)
        print("create vcf reader")

    def get_variants(self):
        fields = list(self.get_fields())
        self.device.seek(0)

        vcf_reader = vcf.Reader(self.device)

        for record in vcf_reader:

            for index, alt in enumerate(record.ALT):
                variant = {
                    "chr": record.CHROM,
                    "pos": record.POS,
                    "ref": record.REF,
                    "alt": str(alt),
                }

                # Read annotations
                for field in fields:
                    category = field["category"]
                    name = field["name"]
                    ftype = field["value_type"]
                    colname = name
                    value = None

                    # PARSE INFO
                    if category == "info":
                        # Test flags
                        if ftype == "Flag":
                            variant[colname] = True if name in record.INFO else False
                        else:
                            if name in record.INFO:
                                if isinstance(record.INFO[name], list):
                                    value = record.INFO[name][0]
                                else:
                                    value = record.INFO[name]
                            variant[colname] = value

                    #         # PARSE GENOTYPE / SAMPLE
                    if category == "sample":
                        for sample in record.samples:
                            sname = name.split("_")[0]

                            for key, value in sample.data._asdict().items():
                                colname = sname + "_" + key
                                variant[colname] = str(value)

            yield variant

    def get_fields(self):

        yield {
            "name": "chr",
            "category": "variant",
            "description": "chromosom",
            "value_type": "String",
        }
        yield {
            "name": "pos",
            "category": "variant",
            "description": "chromosom",
            "value_type": "Integer",
        }
        yield {
            "name": "ref",
            "category": "variant",
            "description": "chromosom",
            "value_type": "String",
        }
        yield {
            "name": "alt",
            "category": "variant",
            "description": "chromosom",
            "value_type": "String",
        }

        self.device.seek(0)
        vcf_reader = vcf.Reader(self.device)
        for key, info in vcf_reader.infos.items():
            yield {
                "name": key,
                "category": "info",
                "description": info.desc,
                "value_type": VcfReader.type_mapping.get(info.type, "String"),
            }

        for sample in vcf_reader.samples:
            for key, val in vcf_reader.formats.items():
                yield {
                    "name": sample + "_" + key,
                    "category": "sample",
                    "description": val.desc,
                    "value_type": VcfReader.type_mapping.get(info.type, "String"),
                }
