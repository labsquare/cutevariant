# Standard imports
import re

# Custom imports
from .abstractreader import sanitize_field_name
from cutevariant.commons import logger

LOGGER = logger()

# Dicts of default fields depending to the type of files
# Keys are based on fields in files (in lower case),
# values are the full description of the field; the name is remaped here as
# it wil be shown in the GUI.
# PS: Consequences/annotation_impac/impacts are standardized here:
# https://www.ensembl.org/info/genome/variation/prediction/predicted_data.html#consequences
SNPEFF_ANNOTATION_DEFAULT_FIELDS = {
    "allele": {
        "name": "allele",
        "category": "annotations",
        "description": "Variant allele used to calculate the consequence",
        "type": "str",
    },
    "feature_type": {
        "name": "feature_type",
        "category": "annotations",
        "description": "Type of feature. Currently one of Transcript, RegulatoryFeature, MotifFeature.",
        "type": "str",
    },
    "annotation": {
        "name": "consequence",
        "category": "annotations",
        "description": "Consequence type",
        "type": "str",
    },
    "annotation_impact": {
        "name": "impact",
        "category": "annotations",
        "description": "Impact rating of variant",
        "type": "str",
    },
    "gene_name": {
        "name": "gene",
        "category": "annotations",
        "description": "Gene name",
        "type": "str",
    },
    "gene_id": {
        "name": "gene_id",
        "category": "annotations",
        "description": "Ensemble stable ID of affected gene",
        "type": "str",
    },
    "feature_id": {
        "name": "transcript",
        "category": "annotations",
        "description": "Transcript name",
        "type": "str",
    },
    "transcript_biotype": {
        "name": "biotype",
        "category": "annotations",
        "description": "Biotype",
        "type": "str",
    },
    "hgvs.p": {
        "name": "hgvs_p",
        "category": "annotations",
        "description": "Protein hgvs",
        "type": "str",
    },
    "hgvs.c": {
        "name": "hgvs_c",
        "category": "annotations",
        "description": "Coding hgvs",
        "type": "str",
    },
    "cdna.pos / cdna.length": {
        "name": "cdna_pos",
        "category": "annotations",
        "description": "Relative position of base pair in cDNA sequence",
        "type": "str",
    },
    "cds.pos / cds.length": {
        "name": "cds_pos",
        "category": "annotations",
        "description": "Relative position of base pair in coding sequence",
        "type": "str",
    },
    "aa.pos / aa.length": {
        "name": "aa_pos",
        "category": "annotations",
        "description": "Amino acid position",
        "type": "str",
    },
    "errors / warnings / info": {
        "name": "log",
        "category": "annotations",
        "description": "Logging info",
        "type": "str",
    },
}


VEP_ANNOTATION_DEFAULT_FIELDS = {
    "allele": {
        "name": "allele",
        "category": "annotations",
        "description": "Variant allele used to calculate the consequence",
        "type": "str",
    },
    "consequence": {
        "name": "consequence",
        "category": "annotations",
        "description": "Consequence type",
        "type": "str",
    },
    "impact": {
        "name": "impact",
        "category": "annotations",
        "description": "Impact rating of the variant",
        "type": "str",
    },
    "symbol": {
        "name": "gene",
        "category": "annotations",
        "description": "Gene name",
        "type": "str",
    },
    "gene": {
        "name": "gene_id",
        "category": "annotations",
        "description": "Ensemble stable ID of affected gene",
        "type": "str",
    },
    "feature": {
        "name": "transcript",
        "category": "annotations",
        "description": "Ensemble stable ID of feature",
        "type": "str",
    },
    "feature_type": {
        "name": "feature_type",
        "category": "annotations",
        "description": "Type of feature. Currently one of Transcript, RegulatoryFeature, MotifFeature.",
        "type": "str",
    },
    "biotype": {
        "name": "biotype",
        "category": "annotations",
        "description": "Biotype",
        "type": "str",
    },
    "hgvsp": {
        "name": "hgvs_p",
        "category": "annotations",
        "description": "Protein hgvs",
        "type": "str",
    },
    "hgvsc": {
        "name": "hgvs_c",
        "category": "annotations",
        "description": "Coding hgvs",
        "type": "str",
    },
    "cdna_position": {
        "name": "cdna_pos",
        "category": "annotations",
        "description": "Relative position of base pair in cDNA sequence",
        "type": "str",
    },
    "cds_position": {
        "name": "cds_pos",
        "category": "annotations",
        "description": "Relative position of base pair in coding sequence",
        "type": "str",
    },
    "protein_position": {
        "name": "aa_pos",
        "category": "annotations",
        "description": "Relative position of amino acid in protein",
        "type": "str",
    },
    "amino_acids": {
        "name": "amino_acids",
        "category": "annotations",
        "description": "Reference and variant amino acids; only given if the variant affects the protein-coding sequence",
        "type": "str",
    },
    "codons": {
        "name": "codons",
        "category": "annotations",
        "description": "Reference and variant codon sequence",
        "type": "str",
    },
    "existing_variation": {
        "name": "existing_variation",
        "category": "annotations",
        "description": "Identifier(s) of co-located known variants",
        "type": "str",
    },
}


class BaseParser:
    """Base class that brings together common functions of VepParser and SnpEffParser"""

    def __init__(self):

        # Receive a dict to map default field names:
        # external to internal with descriptions
        # { external_name: { name: internal_name, category: ..., description: ...
        self.annotation_default_fields = dict()

        # Help to remove duplicated fields in annotations
        # If an annotation field is found in this set by the annotation parser
        # BaseParser.handle_descriptions(), it will not be yielded and thus not
        # used by the program.
        self.variant_field_names = set()

        # About self.annotation_field_name
        # The value of this attribute is deliberately None from the base
        # class because it is created when fields are parsed and it is an
        # insurance that the fields have been processed before variants.
        self.annotation_field_name = None

    def handle_descriptions(self, raw_fields: list):
        """Construct annotation_field_name with the fields of the file, and
        yield fields (dictionnaries) with the full description of fields of the file.

        :Example:
            If 'protein_position' field is encountered in a VEP file,
            'self.annotation_field_name' attribute will contain:
            ['protein_position',] and the followwing dictionnary will be yielded::

                {
                    "name": "aa_pos",
                    "category": "annotations",
                    "description": "amino acid pos",
                    "type": "str",
                }

            If a field is not provided, a default dictionary with less
            information is returned::

                {
                    "name": <field_name>,
                    "description": "",
                    "type":"str",
                    "category":"annotations"
                }

        :param raw_fields: List of fields names.
        :type raw_fields: <list>
        :rtype: <generator <dict>>
        """
        for raw_field_name in raw_fields:
            raw_field_name = raw_field_name.strip().lower()

            # Remap field name if it is in default ones
            if raw_field_name in self.annotation_default_fields:
                _f = self.annotation_default_fields[raw_field_name]
            else:
                # Sanitize fields names here
                # PS: If name is in annotation_default_fields it will be modified
                # by the previous condition.
                raw_field_name = sanitize_field_name(raw_field_name)
                _f = {
                    "name": raw_field_name,
                    "description": "",
                    "type": "str",
                    "category": "annotations",
                }

            if _f["name"] in self.variant_field_names:
                # This field is already in variants fields
                # => do not use it!
                # Append None in place of the name of the field
                # with the aim to not break handle_annotations() when it splits
                # the annotation field.
                self.annotation_field_name.append(None)
                LOGGER.info(
                    "handle_descriptions: '%s' field also found in variants; skipped",
                    _f["name"],
                )
                continue

            # Append the name of the field
            self.annotation_field_name.append(_f["name"])
            # Yield full field
            yield _f

    def handle_annotations(self, annotation_key_name, variant):
        """Remove the given key from the variant dict, add "annotations" key with
        the list of annotations into the variant dict.

        .. note:: The given variant is modified in place.

        Structure of "annotations" value::

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
                # Remove duplicated fields in variants, see handle_descriptions()
                if field_name is not None
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
        super().__init__()
        # Dict of dicts
        # annotation field name as keys, descriptions (name/value) as values
        self.annotation_default_fields = VEP_ANNOTATION_DEFAULT_FIELDS

    def parse_fields(self, fields):
        """Generate fields description

        Called by a reader when its get_fields() method is called and when
        an annotation parser is set.

        This function parses special annotation field "csq"/"CSQ",
        other fields are yielded without being affected.

        .. seealso:: :meth:`handle_descriptions`

        :param fields: Tuple of fields.
        :type fields: <tuple <dict>>
        :return: Generator of fields descriptions.
        :rtype: <generator <dict>>
        """
        self.annotation_field_name = list()
        # PS: fields names are already sanitized by VcfReader get_fields()
        # annotations field names will be sanitized in handle_descriptions()

        # Help to remove duplicated fields from annotations
        self.variant_field_names = {
            field["name"] for field in fields if field["name"] != "csq"
        }

        for field in fields:
            if field["name"] == "csq":
                # Handle description field and parse annotations in it
                description = field["description"]
                # Assume description looks like this :
                # ##INFO=<ID=CSQ,Number=.,Type=String,Description="Consequence annotations from Ensembl VEP. Format: field1|field2|..."

                raw_fields = re.search("Format: (.+)", description)[1].split("|")

                # yield full remaped field
                yield from self.handle_descriptions(raw_fields)
            else:
                yield field

    def parse_variants(self, variants):
        """Generate variants data

        This function removes the key "csq" from the variants,
        and add "annotations" key with the list of annotations.

        .. seealso:: :meth:`handle_annotations`

        :param variants: Generator of variants.
        :type variants: <generator <dict>>
        :return: Generator of full variants with "annotations" key.
        :rtype: <generator <dict>>
        """
        if self.annotation_field_name is None:
            raise Exception("Cannot parse variant without parsing first fields")

        for variant in variants:
            if "csq" in variant:
                self.handle_annotations("csq", variant)
            yield variant


class SnpEffParser(BaseParser):
    """Parser for SnpEFF annotations

    .. note:: We assume that the description field looks like this:

        .. code-block:: text

            INFO=<ID=ANN,Number=.,Type=String,Description="Functional annotations: 'Allele | Annotation | Annotation_Impact | Gene_Name | Gene_ID | Feature_Type | Feature_ID | Transcript_BioType | Rank | HGVS.c | HGVS.p | cDNA.pos / cDNA.length |CDS.pos / CDS.length | AA.pos / AA.length | Distance | ERRORS / WARNINGS / INFO' ">
    """

    def __init__(self):
        super().__init__()
        # Dict of dicts
        # annotation field name as keys, descriptions (name/value) as values
        self.annotation_default_fields = SNPEFF_ANNOTATION_DEFAULT_FIELDS

    def parse_fields(self, fields):
        """Generate fields description

        Called by a reader when its get_fields() method is called and when
        an annotation parser is set.

        This function parses special annotation field "ann"/"ANN",
        other fields are yielded without being affected.

        .. seealso:: :meth:`handle_descriptions`

        Input example::

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

        Output example::

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

        :param fields: Generator of fields.
        :type fields: <generator <dict>>
        :return: Generator of full fields descriptions.
        :rtype: <generator <dict>>
        """
        self.annotation_field_name = list()
        fields = tuple(fields)
        # Help to remove duplicated fields from annotations
        self.variant_field_names = {
            field["name"] for field in fields if field["name"] != "ann"
        }

        for field in fields:
            if field["name"] == "ann":
                # Handle description field and parse annotations in it
                description = field["description"]
                # Assume description looks like this :
                # INFO=<ID=ANN,Number=.,Type=String,Description="Functional annotations: 'field1 | field2 | ...' ">

                raw_fields = re.search("'(.+)'", description)[1].split("|")

                # yield full remaped field
                yield from self.handle_descriptions(raw_fields)
            else:
                # Field is not an annotation: do nothing
                yield field

    def parse_variants(self, variants):
        """Generate variants data

        This function removes the key "ann" from the variants,
        and add "annotations" key with the list of annotations.

        .. seealso:: :meth:`handle_annotations`

        :param variants: Generator of variants.
        :type variants: <generator <dict>>
        :return: Generator of full variants with "annotations" key.
        :rtype: <generator <dict>>
        """
        if self.annotation_field_name is None:
            raise Exception("Cannot parse variant without parsing first fields")

        for variant in variants:
            if "ann" in variant:
                # Modify the current variant:
                # remove "ann" data, replace it with "annotations"
                self.handle_annotations("ann", variant)
            yield variant
