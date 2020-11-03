# Standard imports
import vcf

# Custom imports
from .abstractreader import AbstractReader, sanitize_field_name
from .annotationparser import VepParser, SnpEffParser
from cutevariant.commons import logger


# Fixing PyVCF bug
# https://github.com/jamescasbon/PyVCF/pull/320
def _map(self, func, iterable, bad=[".", "", "NA"]):
    """``map``, but make bad values None."""
    return [func(x) if x not in bad else None for x in iterable]


vcf.Reader._map = _map

# End fixing


LOGGER = logger()

VCF_TYPE_MAPPING = {
    "Float": "float",
    "Integer": "int",
    "Flag": "bool",
    "String": "str",
    "Character": "str",
}


class VcfReader(AbstractReader):
    """VCF parser to extract data from vcf file

    .. seealso:: AbstractReader class for more information.

    Attributes:
        annotation_parser (object): Support "VepParser()" and "SnpeffParser()"
    """

    def __init__(self, device, annotation_parser: str = None):
        """Construct a VCF Reader

        .. note::
            Number of lines `number_lines` AND `file_size` is computed in
            AbstractReader class.

        :param device: File device handler returned by open.
        :key annotation_parser (str): "vep" or "snpeff"
            This argument forces the reader to use a specific parser for
            the annotations. By default it's None: no parser will be used,
            annotations will not be taken into account.
        """
        # Note: number of lines is computed in parent class
        super().__init__(device)
        vcf_reader = vcf.VCFReader(device, strict_whitespace=True)
        self.samples = vcf_reader.samples
        self.annotation_parser = None
        self.metadata = vcf_reader.metadata
        self._set_annotation_parser(annotation_parser)
        # Fields descriptions
        self.fields = None

    def get_fields(self):
        """Get full fields descriptions

        This function is called a first time before variants insertion.

        Annotations fields are added here if they exist in the file.

        .. seealso:: :meth:`parse_fields` for basic default fields.

        :return: Tuple of fields.
            Each field is a dict with the following keys:
            `name, category, description, type`.
            Some fields have an additional constraint key when they are destined
            to be a primary key in the database.
            Annotations fields are added here if they exist in the file.
        :rtype: <tuple <dict>>
        """
        if self.fields is None:

            # Sanitize fields names
            # PS: annotations fields names are sanitized by the annotation_parser
            fields = tuple(self.parse_fields())
            for field in fields:
                field["name"] = sanitize_field_name(field["name"])

            if self.annotation_parser:
                # If "ANN" is a field in the current VCF:
                # Remove and parse special annotations
                self.fields = tuple(self.annotation_parser.parse_fields(fields))
            else:
                self.fields = fields
        return self.fields

    def get_variants(self):
        """Get variants as an iterable of dictionnaries

        "annotations" key is added here with the list of annotations if
        they exist in the file.

        .. seealso:: parse_variants()

        :return: Generator of full variants with "annotations" key.
        :rtype: <generator <dict>>
        """

        if self.fields is None:
            # This is a bad caching code ....
            self.get_fields()

        if self.annotation_parser:
            yield from self.annotation_parser.parse_variants(self.parse_variants())
        else:
            yield from self.parse_variants()

    def parse_variants(self):
        """Read file and parse variants

        1 variant is created for each alternative allele detected for each record.
        For each variant we add the corresponding genotype of each sample under
        the key "samples".

        Examples:
            For a record: `"REF": "A", "ALT": ["T", "C"]` with 2 samples with the
            following genotypes: 0/0 and 0/1 (ref/ref and ref/alt).
            We create 2 variants (because of the 2 alternative alleles),
            each with 2 samples with the following genotypes: 0 and 1.

            Where homozygous_ref = 0, heterozygous = 1, homozygous_alt = 2.

            We don't track which alternative allele is in the genotype of the
            sample.

        See Also:
            https://pyvcf.readthedocs.io/en/v0.4.6/INTRO.html
            https://pyvcf.readthedocs.io/en/latest/API.html#vcf.model._Call.gt_type

        See Also:
            :meth:`cutevariant.core.reader.abstractreader.AbstractReader.get_extra_variants`

        :return: Generator of variants.
        :rtype: <generator <dict>>
        """
        # loop over record
        self.device.seek(0)
        vcf_reader = vcf.VCFReader(self.device, strict_whitespace=True) # TODO use class attr

        # Genotype format fields
        format_fields = set(map(str.lower, vcf_reader.formats))
        # Remove gt field (added manually later)
        format_fields.discard("gt")

        for record in vcf_reader:

            # split row with multiple alt
            for index, alt in enumerate(record.ALT):
                # Remap some columns
                variant = {
                    "chr": record.CHROM,
                    "pos": record.POS,
                    "ref": record.REF,
                    "alt": str(alt),
                    "rsid": record.ID,  # Avoid id column duplication in DB
                    "qual": record.QUAL,
                    "filter": "" if record.FILTER is None else ",".join(record.FILTER),
                }

                forbidden_field = ("chr", "pos", "ref", "alt", "rsid", "qual", "filter")

                # Parse info
                for name in record.INFO:
                    if name.lower() not in forbidden_field:
                        if isinstance(record.INFO[name], list):
                            variant[name.lower()] = ",".join(
                                [str(i) for i in record.INFO[name]]
                            )
                        else:
                            variant[name.lower()] = record.INFO[name]

                # Parse sample(s)
                if record.samples:
                    variant["samples"] = []
                    for sample in record.samples:
                        # New sample data
                        sample_data = {
                            "name": sample.sample,
                            "gt": -1 if sample.gt_type is None else sample.gt_type
                        }

                        # Load sample fields
                        # 1 genotype field per format
                        # In theory: All same fields for each sample
                        for gt_field in format_fields:
                            try:
                                value = sample[gt_field]
                                if isinstance(value, list):
                                    value = ",".join(str(i) for i in value)
                                sample_data[gt_field] = value
                            except AttributeError:
                                # Some fields defined in VCF header by FORMAT data
                                # are not in genotype fields of records...
                                # LOGGER.debug(
                                #     "VCFReader::parse: alt index %s; %s not defined in genotype ", index, gt_field
                                # )
                                pass
                        variant["samples"].append(sample_data)

                yield variant

    def parse_fields(self):
        """Extract fields informations from VCF fields

        .. note:: Fields used in PRIMARY KEYS have the constraint NOT NULL.
            By default, all other fields can have NULL values.

        :return: Generator of fields.
            Each field is a dict with the following keys:
            `name, category, description, type`.
            Some fields have an additional constraint key when they are destined
            to be a primary key in the database.
        :rtype: <generator <dict>>
        """
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
        yield {
            "name": "rsid",
            "category": "variants",
            "description": "rsid unique identifier (see dbSNP)",
            "type": "str",
        }
        yield {
            "name": "qual",
            "category": "variants",
            "description": "Phred-scaled quality score for the assertion made in ALT:"
                           "−10log10 prob(call in ALT is wrong).",
            "type": "int",
        }
        yield {
            "name": "filter",
            "category": "variants",
            "description": "Filter status: PASS if this position has passed all filters.",
            "type": "str",
        }

        # Read VCF
        self.device.seek(0)
        vcf_reader = vcf.VCFReader(self.device, strict_whitespace=True)

        # Read VCF INFO fields
        for field_name, info in vcf_reader.infos.items():

            # if key == "ANN": # Parse special annotation
            #     yield from self.parser.parse_fields(info.desc)
            # else:

            yield {
                "name": field_name.lower(),
                "category": "variants",
                "description": info.desc,
                "type": VCF_TYPE_MAPPING[info.type],
            }

        # Read VCF FORMAT fields
        for field_name, info in vcf_reader.formats.items():
            description = info.desc

            if field_name == "GT":
                # Edit description of Genotype field
                description += " (0: homozygous_ref, 1: heterozygous, 2: homozygous_alt)"

            yield {
                "name": field_name.lower(),
                "category": "samples",
                "description": description,
                "type": VCF_TYPE_MAPPING[info.type],
            }

    def get_samples(self):
        """Return list of samples (individual ids)."""
        return self.samples

    def _set_annotation_parser(self, parser: str):
        """Set the given annotation parser"""
        if parser == "vep":
            self.annotation_parser = VepParser()

        if parser == "snpeff":
            self.annotation_parser = SnpEffParser()

    def __repr__(self):
        return f"VCF Reader using {type(self.annotation_parser).__name__}"

    def get_metadatas(self):
        """override from AbstractReader"""
        output = {"filename": self.device.name}

        for key, value in self.metadata.items():
            output[key] = str(value)

        return output
