from .abstractreader import AbstractReader
import vcf


VCF_TYPE_MAPPING = {
        "Float": "float",
        "Integer": "int",
        "Flag": "bool",
        "String": "str",
    }

SNPEFF_ANNOTATION_DEFAULT_FIELDS = {
    "annotation": {
        "name": "consequence",
        "category": "annotation",
        "description": "consequence",
        "type": "str",
    },
    "annotation_impact": {
        "name": "impact",
        "category": "annotation",
        "description": "impact of variant",
        "type": "str",
    },
    "gene_name": {
        "name": "gene",
        "category": "annotation",
        "description": "gene name",
        "type": "str",
    },
    "gene_id": {
        "name": "gene_id",
        "category": "annotation",
        "description": "gene name",
        "type": "str",
    },
    "feature_id": {
        "name": "transcript",
        "category": "annotation",
        "description": "transcript name",
        "type": "str",
    },
    "transcript_biotype": {
        "name": "biotype",
        "category": "annotation",
        "description": " biotype",
        "type": "str",
    },
    "hgvs.p": {
        "name": "hgvs_p",
        "category": "annotation",
        "description": "protein hgvs",
        "type": "str",
    },
    "hgvs.c": {
        "name": "hgvs_c",
        "category": "annotation",
        "description": "coding hgvs",
        "type": "str",
    },
}


class AnnotationParser(object):



    def parse_fields(self, raw):
        self.fields_index = {}  ## required for parse_variant
        for index, field in enumerate(raw.split("|")):
            key = field.strip().lower()

            if key in SNPEFF_ANNOTATION_DEFAULT_FIELDS.keys():
                self.fields_index[index] = SNPEFF_ANNOTATION_DEFAULT_FIELDS[key]["name"]
                yield SNPEFF_ANNOTATION_DEFAULT_FIELDS[key]

    def parse_variant(self, raw):

        annotation = {}
        for index, ann in enumerate(raw.split("|")):
            if index in self.fields_index:
                field_name = self.fields_index[index]
                annotation[field_name] = ann

        return annotation


class VcfReader(AbstractReader):


    def __init__(self, device):
        super().__init__(device)
        self.parser = AnnotationParser()
        
        vcf_reader = vcf.VCFReader(device)
        self.samples = vcf_reader.samples
        


    def get_fields(self):
        # Remove duplicate
        names = [] 
        for field in self.parse_fields():
            if field["name"] not in names:
                names.append(field["name"])
                yield field



    def get_variants(self):
        yield from self.parse_variants()

    def parse_variants(self):
        """ Extract Variants from VCF file """ 

        # get avaible fields
        fields = list(self.parse_fields())

        #loop over record
        self.device.seek(0)
        vcf_reader = vcf.VCFReader(self.device)
        for record in vcf_reader:
            # split row with multiple alt 
            for index, alt in enumerate(record.ALT):
                variant = {
                    "chr": record.CHROM,
                    "pos": record.POS,
                    "ref": record.REF,
                    "alt": str(alt)
                }


                #Parse info 
                for name in record.INFO:
                    if isinstance(record.INFO[name], list):
                        variant[name] =",".join([str(i) for i in record.INFO[name]])
                    else:
                        variant[name] = record.INFO[name]


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
            "type": "str"
        }
        yield {
            "name": "pos",
            "category": "variant",
            "description": "position",
            "type": "int"
        }

        yield {
            "name": "rsid",
            "category": "variant",
            "description": "rsid",
            "type": "str"
        }

        yield {
            "name": "ref",
            "category": "variant",
            "description": "reference base",
            "type": "str"
        }
        yield {
            "name": "alt",
            "category": "variant",
            "description": "alternative base",
            "type": "str"
        }

        yield {
            "name": "qual",
            "category": "variant",
            "description": "quality",
            "type": "int"
        }

        yield {
            "name": "filter",
            "category": "variant",
            "description": "filter",
            "type": "str"
        }

        # Reads VCF INFO  
        self.device.seek(0)
        vcf_reader = vcf.VCFReader(self.device)
        
        # Reads VCF info 
        for key, info in vcf_reader.infos.items():

            # if key == "ANN": # Parse special annotation
            #     yield from self.parser.parse_fields(info.desc)
            # else:
            yield {
                "name": key,
                "category": "info",
                "description": info.desc,
                "type": VCF_TYPE_MAPPING[info.type]
                }

        # Reads VCF FORMAT             
        for key,info in vcf_reader.formats.items():
            yield {
            "name": key,
            "category":"sample",
            "description": info.desc,
            "type": VCF_TYPE_MAPPING[info.type]
            }


    def get_samples(self):
        return self.samples
