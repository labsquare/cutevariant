# Standard imports
import re

# Custom imports
from cutevariant.commons import logger

LOGGER = logger()

# Dicts of default fields depending to the type of files
SNPEFF_ANNOTATION_DEFAULT_FIELDS = {
    "annotation": {
        "name": "consequence",
        "category": "annotations",
        "description": "consequence",
        "type": "str",
    },
    "annotation_impact": {
        "name": "impact",
        "category": "annotations",
        "description": "impact of variant",
        "type": "str",
    },
    "gene_name": {
        "name": "gene",
        "category": "annotations",
        "description": "gene name",
        "type": "str",
    },
    "gene_id": {
        "name": "gene_id",
        "category": "annotations",
        "description": "gene name",
        "type": "str",
    },
    "feature_id": {
        "name": "transcript",
        "category": "annotations",
        "description": "transcript name",
        "type": "str",
    },
    "transcript_biotype": {
        "name": "biotype",
        "category": "annotations",
        "description": " biotype",
        "type": "str",
    },
    "hgvs.p": {
        "name": "hgvs_p",
        "category": "annotations",
        "description": "protein hgvs",
        "type": "str",
    },
    "hgvs.c": {
        "name": "hgvs_c",
        "category": "annotations",
        "description": "coding hgvs",
        "type": "str",
    },
    "cdna.pos / cdna.length": {
        "name": "cdna_pos",
        "category": "annotations",
        "description": "cdna pos",
        "type": "str",
    },
    "cds.pos / cds.length": {
        "name": "cds_pos",
        "category": "annotations",
        "description": "cds pos",
        "type": "str",
    },
    "aa.pos / aa.length": {
        "name": "aa_pos",
        "category": "annotations",
        "description": "amino acid pos",
        "type": "str",
    },
    "errors / warnings / info": {
        "name": "log",
        "category": "annotations",
        "description": "amino acid pos",
        "type": "str",
    },
}


VEP_ANNOTATION_DEFAULT_FIELDS = {
    "allele": {
        "name": "allele",
        "category": "annotations",
        "description": "allele",
        "type": "str",
    },
    "consequence": {
        "name": "consequence",
        "category": "annotations",
        "description": "impact of variant",
        "type": "str",
    },
    "symbol": {
        "name": "gene",
        "category": "annotations",
        "description": "gene name",
        "type": "str",
    },
    "gene": {
        "name": "gene_id",
        "category": "annotations",
        "description": "gene name",
        "type": "str",
    },
    "feature": {
        "name": "transcript",
        "category": "annotations",
        "description": "transcript name",
        "type": "str",
    },
    "biotype": {
        "name": "biotype",
        "category": "annotations",
        "description": " biotype",
        "type": "str",
    },
    "hgvsp": {
        "name": "hgvs_p",
        "category": "annotations",
        "description": "protein hgvs",
        "type": "str",
    },
    "hgvsc": {
        "name": "hgvs_c",
        "category": "annotations",
        "description": "coding hgvs",
        "type": "str",
    },
    "cdna_position": {
        "name": "cdna_pos",
        "category": "annotations",
        "description": "cdna pos",
        "type": "str",
    },
    "cds_position": {
        "name": "cds_pos",
        "category": "annotations",
        "description": "cds pos",
        "type": "str",
    },
    "protein_position": {
        "name": "aa_pos",
        "category": "annotations",
        "description": "amino acid pos",
        "type": "str",
    },
}


class BaseParser:
    """Base class that brings together common functions of VepParser and SnpEffParser
    """

    def handle_descriptions(self, raw_fields: list):
        """Construct annotation_field_name with the fields of the file, and
        yield fields (dictionnaries) with the full description of fields of the file.

        :Example:
            If 'protein_position' field is encountered in a VEP file,
            'self.annotation_field_name' attribute will contain:
            ['protein_position',] and the followwing dictionnary will be yielded:
            {
                "name": "aa_pos",
                "category": "annotations",
                "description": "amino acid pos",
                "type": "str",
            }

            If a field is not provided, a default dictionary with less
            information is returned:
            {
                "name": <field_name>,
                "description": "None",
                "type":"str",
                "category":"annotations"
            }

        :param raw_fields: List of fields names.
        :type raw_fields: <list>
        :rtype: <generator <dict>>
        """
        for i in raw_fields:
            i = i.strip().lower()

            # Remap field name if it is in default ones
            if i in self.annotation_default_fields:
                _f = self.annotation_default_fields[i]
            else:
                _f = {
                    "name": i,
                    "description": "None",
                    "type": "str",
                    "category": "annotations",
                }

            # Append the name of the field
            self.annotation_field_name.append(_f["name"])
            # Yield full field
            yield _f

    def handle_annotations(self, annotation_key_name, variant):
        """Remove the given key from the variant dict, add "annotations" key with
        the list of annotations into the variant dict.

        .. note:: The given variant is modified in place.
        .. note:: Structure of "annotations" value:
            [{
                'annotation_field_name1': 'data1',
                'annotation_field_name2': 'data2',
                ...
            },]
            "annotations" is a list since there may be multiple annotations for
            a variant.
        """
        raw = variant.pop(annotation_key_name)

        annotations = list()
        for transcripts in raw.split(","):
            transcript = transcripts.split("|")

            if len(self.annotation_field_name) != len(transcript):
                LOGGER.error(
                    "BaseParser:handle_annotations:: Missing field in the "
                    "annotations of the following variant:\n%s\n"
                    "These annotations will be skipped!",
                    variant,
                )
                continue

            annotation = {
                field_name: transcript[idx]
                for idx, field_name in enumerate(self.annotation_field_name)
            }
            annotations.append(annotation)

        # Avoid setting empty list to the variant => generates a SQL query issue
        if annotations:
            variant["annotations"] = annotations


class VepParser(BaseParser):
    """Parser of VEP annotations

    .. note:: We assume that the description field looks like this:
        ##INFO=<ID=CSQ,Number=.,Type=String,Description="Consequence annotations from Ensembl VEP. Format: Allele|Consequence|IMPACT|SYMBOL|Gene|Feature_type|Featur.."
    """

    def __init__(self):
        # Dict of dicts
        # annotation field name as keys, descriptions (name/value) as values
        self.annotation_default_fields = VEP_ANNOTATION_DEFAULT_FIELDS

    def parse_fields(self, fields):

        self.annotation_field_name = list()
        for field in fields:
            if field["name"] == "csq":
                description = field["description"]
                # Assume description looks like this :
                # ##INFO=<ID=CSQ,Number=.,Type=String,Description="Consequence annotations from Ensembl VEP. Format: field1|field2|..."

                raw_fields = re.search("Format: (.+)", description)[1].split("|")

                for field_description in self.handle_descriptions(raw_fields):
                    yield field_description
            else:
                yield field

    def parse_variants(self, variants):
        if not hasattr(self, "annotation_field_name"):
            raise Exception("Cannot parse variant without parsing first fields")

        for variant in variants:
            if "csq" in variant:
                self.handle_annotations("csq", variant)
            yield variant


class SnpEffParser(BaseParser):
    """Parser for SnpEFF annotations

    .. note:: We assume that the description field looks like this:
        INFO=<ID=ANN,Number=.,Type=String,Description="Functional annotations: 'Allele | Annotation | Annotation_Impact | Gene_Name | Gene_ID | Feature_Type | Feature_ID | Transcript_BioType | Rank | HGVS.c | HGVS.p | cDNA.pos / cDNA.length |CDS.pos / CDS.length | AA.pos / AA.length | Distance | ERRORS / WARNINGS / INFO' ">
    """

    def __init__(self):
        # Dict of dicts
        # annotation field name as keys, descriptions (name/value) as values
        self.annotation_default_fields = SNPEFF_ANNOTATION_DEFAULT_FIELDS

    def parse_fields(self, fields):
        """Generate fields description

        This function parses special annotation field "ann"/"ANN",
        other fields are yielded without being affected.

        .. seealso:: handle_descriptions()

        :Input example:
            ({
            'name': 'generic_field1',
            'description': ...
            'category': ...
            'type': ...
            },
            {
            'name': 'ann',
            'description': '... annotation_field_name1 | annotation_field_name2 ...',
            ...
            })

        :Output example:
            ({
            'name': 'generic_field1',
            'description': ...
            'category': ...
            'type': ...
            },
            {
            'name': 'annotation_field_name1',
            'description': ...
            'category': ...
            'type': ...
            },
            {
            'name': 'annotation_field_name2',
            'description': ...
            'category': ...
            'type': ...
            })

        .. note:: Names of fields are changed to lowercase.

        :return: Generator of fields descriptions.
        :rtype: <generator <dict>>
        """
        self.annotation_field_name = list()
        for field in fields:
            if field["name"] == "ann":
                description = field["description"]
                # Assume description looks like this :
                # INFO=<ID=ANN,Number=.,Type=String,Description="Functional annotations: 'field1 | field2 | ...' ">

                raw_fields = re.search("'(.+)'", description)[1].split("|")

                for field_description in self.handle_descriptions(raw_fields):
                    # yield full remaped field
                    yield field_description
            else:
                # Field is not an annotation: do nothing
                yield field

    def parse_variants(self, variants):
        """Generate variants data

        This function removes the key "ann" from the variants,
        and add "annotations" key with the list of annotations.

        .. seelalso:: handle_annotations()
        """
        if not hasattr(self, "annotation_field_name"):
            raise Exception("Cannot parse variant without parsing first fields")

        for variant in variants:
            if "ann" in variant:
                # Modify the current variant:
                # remove "ann" data, replace it with "annotations"
                self.handle_annotations("ann", variant)
            yield variant
