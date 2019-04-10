import copy
import re

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

    "cdna.pos / cdna.length" : {
        "name": "cdna_pos",
        "category": "annotation",
        "description": "cdna pos",
        "type": "str",
    },
    "cds.pos / cds.length": {
        "name": "cds_pos",
        "category": "annotation",
        "description": "cds pos",
        "type": "str",
    },
    "aa.pos / aa.length" :{
        "name": "aa_pos",
        "category": "annotation",
        "description": "amino acid pos",
        "type": "str",
    },
    "errors / warnings / info" :{
        "name": "log",
        "category": "annotation",
        "description": "amino acid pos",
        "type": "str",
    }
}


VEP_ANNOTATION_DEFAULT_FIELDS = {
    "allele": {
        "name": "consequence",
        "category": "annotation",
        "description": "consequence",
        "type": "str",
    },
    "consequence": {
        "name": "consequence",
        "category": "annotation",
        "description": "impact of variant",
        "type": "str",
    },
    "symbol": {
        "name": "gene",
        "category": "annotation",
        "description": "gene name",
        "type": "str",
    },
    "gene": {
        "name": "gene_id",
        "category": "annotation",
        "description": "gene name",
        "type": "str",
    },
    "feature": {
        "name": "transcript",
        "category": "annotation",
        "description": "transcript name",
        "type": "str",
    },
    "biotype": {
        "name": "biotype",
        "category": "annotation",
        "description": " biotype",
        "type": "str",
    },
    "hgvsp": {
        "name": "hgvs_p",
        "category": "annotation",
        "description": "protein hgvs",
        "type": "str",
    },
    "hgvsc": {
        "name": "hgvs_c",
        "category": "annotation",
        "description": "coding hgvs",
        "type": "str",
    },

    "cdna_position" : {
        "name": "cdna_pos",
        "category": "annotation",
        "description": "cdna pos",
        "type": "str",
    },
    "cds_position": {
        "name": "cds_pos",
        "category": "annotation",
        "description": "cds pos",
        "type": "str",
    },
    "protein_position" :{
        "name": "aa_pos",
        "category": "annotation",
        "description": "amino acid pos",
        "type": "str",
    }
}



class VepParser(object):

    def parse_fields(self,fields):
        self.annotation_field_name = []
        for field in fields:
            if field["name"] == "csq":
                description =  field["description"] 
                 # Assume description looks like this : 
                 # ##INFO=<ID=CSQ,Number=.,Type=String,Description="Consequence annotations from Ensembl VEP. Format: Allele|Consequence|IMPACT|SYMBOL|Gene|Feature_type|Featur.."

                raw_fields = re.search("Format: (.+)", description)[1].split("|")

                for i in raw_fields:
                    i = i.strip().lower()

                    if i in VEP_ANNOTATION_DEFAULT_FIELDS:
                        _f = VEP_ANNOTATION_DEFAULT_FIELDS[i]
                    else:
                        _f = {"name": i, "description": "None", "type":"str", "category":"annotation"}

                    self.annotation_field_name.append(_f["name"])
                    yield _f
            else:
                yield field

    def parse_variants(self, variants):
        if not hasattr(self,"annotation_field_name"):
            raise Exception("Cannot parse variant without parsing first fields")
        for variant in variants:
            if "csq" in variant:
                raw = variant.pop("csq")
                variant["annotations"] = []
                for transcripts in raw.split(","):
                    new_variant = copy.copy(variant) 
                    transcript = transcripts.split("|")
                    annotation = {}
                    for idx, field_name in enumerate(self.annotation_field_name):
                        annotation[field_name] = transcript[idx]
                    variant["annotations"].append(annotation)
                yield variant
            else:
                yield variant 



class SnpEffParser(object):

    def parse_fields(self,fields):
        self.annotation_field_name = []
        for field in fields:
            if field["name"] == "ann":
                description = field["description"]
                # Assume description looks like this : 
                # INFO=<ID=ANN,Number=.,Type=String,Description="Functional annotations: 'Allele | Annotation | Annotation_Impact | Gene_Name | Gene_ID | Feature_Type | Feature_ID | Transcript_BioType | Rank | HGVS.c | HGVS.p | cDNA.pos / cDNA.length |CDS.pos / CDS.length | AA.pos / AA.length | Distance | ERRORS / WARNINGS / INFO' ">

                raw_fields = re.search("\'(.+)\'", description)[1].split("|")

                for i in raw_fields:
                    i = i.strip().lower()

                    # Remap field name 
                    if i in SNPEFF_ANNOTATION_DEFAULT_FIELDS:
                        _f = SNPEFF_ANNOTATION_DEFAULT_FIELDS[i]
                    else:
                        _f = {"name": i, "description": "None", "type":"str", "category":"annotation"}

                    self.annotation_field_name.append(_f["name"])
                    yield _f
            else:
                yield field

    def parse_variants(self, variants):

        if not hasattr(self,"annotation_field_name"):
            raise Exception("Cannot parse variant without parsing first fields")

        for variant in variants:
            if "ann" in variant:
                raw = variant.pop("ann")
                variant["annotations"] = []
                for transcripts in raw.split(","):
                    new_variant = copy.copy(variant) 
                    transcript = transcripts.split("|")
                    annotation = {}
                    for idx, field_name in enumerate(self.annotation_field_name):
                        annotation[field_name] = transcript[idx]
                    variant["annotations"].append(annotation)
                yield variant
            else:
                yield variant 
