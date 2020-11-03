# Standard imports
import csv

# Custom imports
from .abstractreader import AbstractReader
from .annotationparser import VEP_ANNOTATION_DEFAULT_FIELDS, BaseParser
from cutevariant.commons import logger

LOGGER = logger()


class CsvReader(AbstractReader):
    """VEP parser to extract data from CSV file

    .. seealso:: AbstractReader class for more information.

    About VEP file format:

    http://www.ensembl.org/info/docs/tools/vep/script/vep_other.html#pick

    If a variant overlaps a gene with multiple alternate splicing variants
    (transcripts), then a block of annotation for each of these transcripts
    is reported in the output. In the default VEP output format each of these
    blocks is written on a single line of output; in VCF output format the
    blocks are separated by commas in the INFO field.

    Example of annotation block (1 line)::

        #Uploaded_variation   Location   Allele   Consequence   IMPACT
        SYMBOL   Gene   Feature_type   Feature   BIOTYPE   EXON   INTRON   HGVSc
        HGVSp   cDNA_position   CDS_position   Protein_position
        Amino_acids   Codons   Existing_variation   DISTANCE
        STRAND   FLAGS   SYMBOL_SOURCE   HGNC_ID   TSL   APPRIS
        REFSEQ_MATCHGIVEN_REF   USED_REF   BAM_EDIT
        SIFT   PolyPhen   AF   CLIN_SIG   SOMATIC   PHENO
        PUBMED   MOTIF_NAME   MOTIF_POS   HIGH_INF_POS   MOTIF_SCORE_CHANGE
        LRT_pred   LRT_score   MutationTaster_model   MutationTaster_pred
        SIFT_pred   SIFT_score   clinvar_clnsig   clinvar_rs   clinvar_trait
    """

    def __init__(self, device):
        # Note: number of lines is computed in parent class
        super().__init__(device)

        # Quick tests on the input file...
        first_line = device.readline()
        csv_dialect = csv.Sniffer().sniff(first_line)

        # Is this file has a correct header ?
        # Test 2 first lines
        header = csv.Sniffer().has_header(first_line + device.readline())
        if not header:
            raise Exception("No header detected in the file; not a CSV file?")

        # Build a csv reader
        self.device.seek(0)
        self.csv_reader = csv.DictReader(self.device, dialect=csv_dialect)

        # hacky hacky...
        # We use BaseParser here only for its function handle_descriptions()
        # that generate full description of annotation fields by taking into
        # account default supported fields set by with VEP_ANNOTATION_DEFAULT_FIELDS
        self.annotation_parser = BaseParser()
        self.annotation_parser.annotation_default_fields = VEP_ANNOTATION_DEFAULT_FIELDS

        # Some columns are ignored or mapped manually to standard ones
        # (chr, pos, ref, alt)
        self.ignored_columns = (
            "location",
            "allele",
            "#uploaded_variation",
            "given_ref",
            "used_ref",
        )

        # Fields descriptions
        self.fields = None

        LOGGER.debug(
            "CsvReader::init: CSV fields found: %s", self.csv_reader.fieldnames
        )

    def __del__(self):
        del self.device

    def get_fields(self):
        """Get full fields descriptions

        .. note:: Annotations fields are added here if they exist in the file.

        .. seealso:: :meth:`parse_fields` for basic default fields.

        :return: Tuple of fields.
            Each field is a dict with the following keys:
            `name, category, description, type`.
            Some fields have an additional constraint key when they are destined
            to be a primary key in the database.
            Annotations fields are added here if they exist in the file.
        :rtype: <tuple <dict>>
        """
        LOGGER.debug("CsvReader::get_fields: called")
        if not self.fields:
            LOGGER.debug("CsvReader::get_fields: parse")
            self.fields = tuple(self.parse_fields())
        return self.fields

    def get_variants(self):
        """Get variants as an iterable of dictionnaries

        "annotations" key is added here with the list of annotations if
        they exist in the file.

        .. seealso:: parse_variant()

        :return: Generator of full variants with "annotations" key.
        :rtype: <generator <dict>>
        """
        yield from self.parse_variants()

    def get_samples(self):
        """Return samples (individual/family data) of the file (empty list for this reader)"""
        return []

    def parse_fields(self):
        """See :meth:`get_fields`"""
        yield {
            "name": "chr",
            "category": "variants",
            "description": "Chromosome",
            "type": "str",
            "constraint": "NOT NULL",
        }
        yield {
            "name": "pos",
            "category": "variants",
            "description": "Reference position, with the 1st base having position 1",
            "type": "int",
            "constraint": "NOT NULL",
        }
        yield {
            "name": "ref",
            "category": "variants",
            "description": "Reference base",
            "type": "str",
            "constraint": "NOT NULL",
        }
        yield {
            "name": "alt",
            "category": "variants",
            "description": "Alternative base",
            "type": "str",
            "constraint": "NOT NULL",
        }

        # Get all fields (except the ignored ones)
        raw_fields = (
            field
            for field in self.csv_reader.fieldnames
            if field.lower() not in self.ignored_columns
        )
        # yield full remaped field
        # Hack fix this... the Base class should possess this attribute
        self.annotation_parser.annotation_field_name = list()
        yield from self.annotation_parser.handle_descriptions(raw_fields)

    def parse_variants(self):
        """Read file and parse variants

        .. todo: Handle samples

        .. note:: Each line is a transcript; there are many transcripts per variant.

        :return: Generator of variants.
        :rtype: <generator <dict>>
        """

        def add_annotation_to_variant():
            """Add annotation to the current variant"""
            # No annotation parsed
            if not annotation:
                return
            annotations = variant.get("annotations")
            if annotations:
                # Update
                annotations.append(annotation)
            else:
                # Set
                variant["annotations"] = [annotation]

        if self.annotation_parser.annotation_field_name is None:
            raise Exception("Cannot parse variant without parsing fields first")

        variants = dict()
        transcript_idx = 0
        for transcript_idx, row in enumerate(self.csv_reader, 1):

            # Build primary key by mapping existing fields in the original file
            chrom, pos = self.location_to_chr_pos(row["Location"])
            ref = row["GIVEN_REF"]
            alt = row["Allele"]

            if "USED_REF" in row:
                # Check consistency
                assert row["GIVEN_REF"] == row["USED_REF"], "GIVEN_REF != USED_REF"

            primary_key = (chrom, pos, ref, alt)
            # Get previous variant with same primary key (previous transcript)
            variant = variants.get(primary_key, dict())

            # filtre les champs non voulus, cherche ceux qui restent dans
            # VEP_ANNOTATION_DEFAULT_FIELDS pour savoir s'ils sont supportés;
            # sinon les ajoute en lower case en fallback
            annotation = dict()
            # Remove unwanted fields
            g = (key for key in row.keys() if key.lower() not in self.ignored_columns)
            for raw_key in g:
                lower_key = raw_key.lower()
                # Get supported fields
                field_descript = VEP_ANNOTATION_DEFAULT_FIELDS.get(lower_key)
                if field_descript:
                    # Use supported field name
                    lower_key = field_descript["name"]

                annotation[lower_key] = row[raw_key]

            # Quicker ?
            # annotation = {
            #    VEP_ANNOTATION_DEFAULT_FIELDS.get(key.lower(), {'name': key.lower()})['name']: value
            #    for key, value in row.items() if key.lower() not in self.ignored_columns
            # }

            if variant:
                # Variant already created
                # Append current annotation to the previous ones
                add_annotation_to_variant()
                continue

            # New variant
            variant["chr"], variant["pos"], variant["ref"], variant["alt"] = primary_key

            # Set current annotation
            add_annotation_to_variant()

            # testing purpose
            #            variant["samples"] = [
            #                {"name": "boby", "gt": 0},
            #                {"name": "sacha", "gt": 1},
            #                {"name": "olivier", "gt": 2},
            #            ]

            variants[primary_key] = variant

        LOGGER.info(
            "CsvReader::parse_variants: transcripts %s, variants %s",
            transcript_idx, len(variants)
        )

        for variant in variants.values():
            yield dict(variant)

    def location_to_chr_pos(self, location: str):
        """Parse VEP `Location` field to extract `chr`, `pos` fields

        2 representations can be encountered in standard coordinate format
            - chr:start
            - chr:start-end

        The start position is always returned as `pos` value.

        :Example:
            11:10000-10000 => chr, pos => 11, 10000

        :param location: Location field in a VEP file.
        :return: Tuple of chr and pos data.
        :rtype: <tuple <str>, <str>>
        """
        chrom, positions = location.split(":")
        pos = positions.split("-")[0]
        return chrom, pos

    def __repr__(self):
        return f"VEP Reader using {type(self.annotation_parser).__name__}"
