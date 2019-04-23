from .abstractreader import AbstractReader
from .annotationparser import VepParser, SnpEffParser
import vcf
import copy



VCF_TYPE_MAPPING = {"Float": "float", "Integer": "int", "Flag": "bool", "String": "str"}


class VcfReader(AbstractReader):
    """
    VCF parser to extract data from vcf file. See Abstract Reader for more information

    Attributes:
        annotation_parser (object): Support "VepParser()" and "SnpeffParser()"    

    ..seealso: AbstractReader 

    """
    def __init__(self, device, annotation_parser:str = None):
        """
        Construct a VCF Reader 

        :param device: file device returned by open 
        :param annotation_parser (str): "vep" or "snpeff" 
        """
        super().__init__(device)

        vcf_reader = vcf.VCFReader(device)
        self.samples = vcf_reader.samples
        self.annotation_parser = None
        self._set_annotation_parser(annotation_parser)


    def _get_fields(self):
        # Remove duplicate

        fields = self.parse_fields()
        if self.annotation_parser:
            return self.annotation_parser.parse_fields(fields)
        else:
            return fields


    def _get_variants(self):
        """ override methode """
        if self.annotation_parser:
            yield from self.annotation_parser.parse_variants(self.parse_variants())
        else:
            yield from self.parse_variants()

    def parse_variants(self):
        """ Read file and parse variants  """

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
                        sample_data["gt"]  =  sample.gt_type
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
            "category": "variants",
            "description": "chromosom",
            "type": "str",
        }
        yield {
            "name": "pos",
            "category": "variants",
            "description": "position",
            "type": "int",
        }

        yield {
            "name": "rsid",
            "category": "variants",
            "description": "rsid",
            "type": "str",
        }

        yield {
            "name": "ref",
            "category": "variants",
            "description": "reference base",
            "type": "str",
        }
        yield {
            "name": "alt",
            "category": "variants",
            "description": "alternative base",
            "type": "str",
        }

        yield {
            "name": "qual",
            "category": "variants",
            "description": "quality",
            "type": "int",
        }

        yield {
            "name": "filter",
            "category": "variants",
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
                "category": "variants",
                "description": info.desc,
                "type": VCF_TYPE_MAPPING[info.type],
            }

        # Reads VCF FORMAT
        for key, info in vcf_reader.formats.items():
            yield {
                "name": key.lower(),
                "category": "samples",
                "description": info.desc,
                "type": VCF_TYPE_MAPPING[info.type],
            }

    def _get_samples(self):
        return self.samples


    # def _keep_unique_fields(self,fields):
    #     ''' return fields list with unique field name ''' 
    #     names = []
    #     for field in fields:
    #         if field["name"] not in names:
    #             names.append(field["name"])
    #             yield field

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