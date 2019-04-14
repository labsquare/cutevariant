from .abstractreader import AbstractReader
from .annotationparser import VepParser, SnpEffParser
import vcf
import copy


VCF_TYPE_MAPPING = {"Float": "float", "Integer": "int", "Flag": "bool", "String": "str"}


class VcfReader(AbstractReader):
    def __init__(self, device, annotation_parser:str = None):
        super().__init__(device)

        vcf_reader = vcf.VCFReader(device)
        self.samples = vcf_reader.samples
        self.annotation_parser = None
        self._set_annotation_parser(annotation_parser)


    def get_fields(self):
        # Remove duplicate
        fields = self.parse_fields()
        if self.annotation_parser:
            yield from self._keep_unique_fields(self.annotation_parser.parse_fields(fields))
        else:
            yield from self._keep_unique_fields(fields)


    def get_variants(self):
        if self.annotation_parser:
            yield from self.annotation_parser.parse_variants(self.parse_variants())
        else:
            yield from self.parse_variants()

    def parse_variants(self):
        """ Extract Variants from VCF file """

        #  get avaible fields
        fields = list(self.parse_fields())

        # loop over record
        self.device.seek(0)
        vcf_reader = vcf.VCFReader(self.device)
        for record in vcf_reader:
            # split row with multiple alt
            for index, alt in enumerate(record.ALT):
                variant = {
                    "chr": record.CHROM,
                    "pos": record.POS,
                    "ref": record.REF,
                    "alt": str(alt),
                    "rsid": record.ID,
                    "qual": record.QUAL,
                    "filter":"" # TODO ? 
                }

                # Parse info
                for name in record.INFO:
                    if isinstance(record.INFO[name], list):
                        variant[name.lower()] = ",".join([str(i) for i in record.INFO[name]])
                    else:
                        variant[name.lower()] = record.INFO[name]

                # parse sample
                if record.samples:
                    variant["samples"] = []
                    for sample in record.samples:
                        sample_data = {}
                        sample_data["name"] = sample.sample

                        for field in record.FORMAT.split(":"):

                            if isinstance(sample[field], list):
                                value = ",".join([str(i) for i in sample[field]])
                            else:
                                value = sample[field]

                            if field == "GT":
                                field = "gt"
                                value = 1

                            sample_data[field] = value

                        variant["samples"].append(sample_data)

                yield variant

                #     # #PARSE Annotation
                #     # if category == "annotation": #=== PARSE Special Annotation ===
                #     #     # each variant can have multiple annotation. Create then many variants
                #     #     variant["annotation"] = []
                #     #     annotations = record.INFO["ANN"]
                #     #     for annotation in annotations:
                #     #         variant["annotation"].append(
                #     #             self.parser.parse_variant(annotation)
                #     #         )

    def parse_fields(self):
        """ Extract fields informations from VCF fields """

        yield {
            "name": "chr",
            "category": "variant",
            "description": "chromosom",
            "type": "str",
        }
        yield {
            "name": "pos",
            "category": "variant",
            "description": "position",
            "type": "int",
        }

        yield {
            "name": "rsid",
            "category": "variant",
            "description": "rsid",
            "type": "str",
        }

        yield {
            "name": "ref",
            "category": "variant",
            "description": "reference base",
            "type": "str",
        }
        yield {
            "name": "alt",
            "category": "variant",
            "description": "alternative base",
            "type": "str",
        }

        yield {
            "name": "qual",
            "category": "variant",
            "description": "quality",
            "type": "int",
        }

        yield {
            "name": "filter",
            "category": "variant",
            "description": "filter",
            "type": "str",
        }

        # Reads VCF INFO
        self.device.seek(0)
        vcf_reader = vcf.VCFReader(self.device)

        #  Reads VCF info
        for key, info in vcf_reader.infos.items():

            # if key == "ANN": # Parse special annotation
            #     yield from self.parser.parse_fields(info.desc)
            # else:
            yield {
                "name": key.lower(),
                "category": "info",
                "description": info.desc,
                "type": VCF_TYPE_MAPPING[info.type],
            }

        # Reads VCF FORMAT
        for key, info in vcf_reader.formats.items():
            yield {
                "name": key.lower(),
                "category": "sample",
                "description": info.desc,
                "type": VCF_TYPE_MAPPING[info.type],
            }

    def get_samples(self):
        return self.samples


    def _keep_unique_fields(self,fields):
        ''' return fields list with unique field name ''' 
        names = []
        for field in fields:
            if field["name"] not in names:
                names.append(field["name"])
                yield field
            # else:
            #     # Rename duplicate fields : field_1, field_2 etc ...
            #     field["name"]  = field["name"] +"_"+ str(names.count(field["name"])+1)
            #     yield field

    def _set_annotation_parser(self, parser: str):
        if parser == "vep":
            self.annotation_parser = VepParser() 

        if parser == "snpeff":
            self.annotation_parser = SnpEffParser()

    def __repr__(self):
        return f"VCF Parser using {type(self.annotation_parser).__name__}"