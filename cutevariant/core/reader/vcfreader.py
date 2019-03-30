from .abstractreader import AbstractReader
import vcf


SNPEFF_ANNOTATION_DEFAULT_FIELDS = {
    "annotation": {
        "name": "consequence",
        "category": "annotation",
        "description": "consequence",
        "type": "text",
    },
    "annotation_impact": {
        "name": "impact",
        "category": "annotation",
        "description": "impact of variant",
        "type": "text",
    },
    "gene_name": {
        "name": "gene",
        "category": "annotation",
        "description": "gene name",
        "type": "text",
    },
    "gene_id": {
        "name": "gene_id",
        "category": "annotation",
        "description": "gene name",
        "type": "text",
    },
    "feature_id": {
        "name": "transcript",
        "category": "annotation",
        "description": "transcript name",
        "type": "text",
    },
    "transcript_biotype": {
        "name": "biotype",
        "category": "annotation",
        "description": " biotype",
        "type": "text",
    },
    "hgvs.p": {
        "name": "hgvs_p",
        "category": "annotation",
        "description": "protein hgvs",
        "type": "text",
    },
    "hgvs.c": {
        "name": "hgvs_c",
        "category": "annotation",
        "description": "coding hgvs",
        "type": "text",
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

    type_mapping = {
        "Float": "Float",
        "Integer": "Integer",
        "Flag": "Boolean",
        "String": "String",
    }

    def __init__(self, device):
        super(VcfReader, self).__init__(device)
        self.parser = AnnotationParser()

    def parse_variants(self):
        fields = list(self.parse_fields())
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
                    ftype = field["type"]
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

                    # PARSE GENOTYPE / SAMPLE
                    if category == "sample":
                        variant["samples"] = list()
                        for sample in record.samples:
                            gt = -1
                            if sample["GT"] == "0/1":
                                gt = 1
                            if sample["GT"] == "0/0":
                                gt = 0
                            if sample["GT"] == "1/1":
                                gt = 2

                            variant["samples"].append({"name": sample.sample, "gt": gt})

                    #  PARSE Annotation
                    if category == "annotation":
                        # each variant can have multiple annotation. Create then many variants
                        variant["annotation"] = []
                        annotations = record.INFO["ANN"]
                        for annotation in annotations:
                            variant["annotation"].append(
                                self.parser.parse_variant(annotation)
                            )

                yield variant

    def parse_fields(self):

        yield {
            "name": "chr",
            "category": "variant",
            "description": "chromosom",
            "type": "text",
        }
        yield {
            "name": "pos",
            "category": "variant",
            "description": "chromosom",
            "type": "integer",
        }
        yield {
            "name": "ref",
            "category": "variant",
            "description": "chromosom",
            "type": "text",
        }
        yield {
            "name": "alt",
            "category": "variant",
            "description": "chromosom",
            "type": "text",
        }

        self.device.seek(0)
        vcf_reader = vcf.Reader(self.device)
        # Annotation ...
        for key, info in vcf_reader.infos.items():
            if key == "ANN":
                yield from self.parser.parse_fields(info.desc)

        # PEUVENT SE METTRE AUTOMATIQUEMENT ...
        for sample in vcf_reader.samples:
            yield {
                "name": f"gt{sample}.gt",
                "category": "sample",
                "description": "sample genotype",
                "type": "text",
            }

    def get_samples(self):
        self.device.seek(0)
        vcf_reader = vcf.Reader(self.device)
        return vcf_reader.samples
