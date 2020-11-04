from abc import ABC, abstractmethod
import io
import gzip
from collections import Counter
import cutevariant.commons as cm

LOGGER = cm.logger()


class AbstractReader(ABC):
    """Base class for all Readers required to import variants into the database.

    Subclass it if you want a new file parser .

    Attributes:

        device: A file object typically returned by open(); Can be None if
            FakeReader type is instanciated.
        file_size: File size in bytes
            See Also: :meth:`self.get_total_file_size`
        number_lines: Number of lines in the file (compressed or not).
            See Also: :meth:`self.compute_number_lines`
        read_bytes: Current bytes readed (progression = read_bytes / file_size)
            It's a fallback if number_lines can't be computed.
        samples: List of samples in the file (default: empty)

    Example:
        >>> with open(filename,"r") as file:
        ...    reader = Reader(file)
        ...    reader.get_variants()
    """

    def __init__(self, device):
        self.device = device
        self.number_lines = None
        self.read_bytes = 0
        self.samples = list()

        self.file_size = self.get_total_file_size()
        self.compute_number_lines()

    @classmethod
    @abstractmethod
    def get_variants(cls):
        """Abstract method must return variants as an iterable of dictionnaries.

        Variant dictionnary has 4 mandatory fields `chr`, `pos`, `ref`, `alt`.
        Other fields are optionnal
        For instance::

            [
                {"chr": "chr3","pos": 3244,"ref": "A","alt":"C", "qual": 30},
                {"chr": "chr4","pos": 3244,"ref": "A","alt":"C","qual": 20},
                {"chr": "chr5","pos": 3244,"ref": "A","alt":"C","qual": 10 },
            ]

        Annotations and Samples objects can be embbeded into a variant dictionnaries.
        Annotations describes several annotations for one variant.
        In the most of the case, those are relative to transcripts.
        Samples describes information relative to a variant with a sample,
        like genotype (gt). This is a mandatory field.

        .. code-block:: python

            [{
                "chr": "chr3",
                "pos": 3244,
                "ref": "A",
                "alt":"C",
                "field_n": "value_n",
                "annotations": [
                    {"gene": "GJB2", "transcripts": "NM_00232.1", "field_n": "value_n"},
                    {"gene": "GJB2", "transcripts": "NM_00232.2", "field_n": "value_n"}
                ],
                "samples": [
                    {"name":"boby", "genotype": 1, "field_n":"value_n"},
                    {"name":"kevin", "genotype": 1, "field_n":"value_n"}
                ]
            },]

        Yields:
            dict: variant dictionnary

        Examples:
            >>> for variant in reader.get_variants():
            ...     print(variant["chr"], variant["pos"])

        """
        raise NotImplementedError(cls.__class__.__name__)

    @classmethod
    @abstractmethod
    def get_fields(cls):
        """Abstract method hat must return fields description

        Full output::

            [
            {"name": "chr", "type": "text", "category": "variant", "description": "..."},
            {"name": "pos", "type": "text", "category": "variant", "description": "..."},
            {"name": "ref", "type": "text", "category": "variant", "description": "..."},
            {"name": "alt", "type": "text", "category": "variant", "description": "..."},
            {"name": "field_n", "type": "text", "category": "variant", "description": "..."},
            {"name": "name", "type": "text", "category": "annotations", "samples": "..."},
            {"name": "genotype", "type": "text", "category": "annotations", "samples": "..."}
            ]

        Yields:
            dict: field dictionnary

        Examples:
            >>> for field in reader.get_fields():
            ...     print(field["name"], field["description"])
        """
        raise NotImplementedError(cls.__class__.__name__)

    def get_samples(self) -> list:
        """Return list of samples

        Override this method to have samples in sqlite database.
        """
        return []

    def get_metadatas(self) -> dict:
        """Get meta data

        Override this method to have meta data in sqlite database
        """
        return {}

    def get_extra_fields(self):
        """Yield fields with extra mandatory fields like 'comment' and 'score'"""
        yield {
            "name": "favorite",
            "type": "bool",
            "category": "variants",
            "description": "Tag status as favorite",
        }
        yield {
            "name": "comment",
            "type": "str",
            "category": "variants",
            "description": "Variant comment written by user",
        }
        yield {
            "name": "classification",
            "type": "int",
            "category": "variants",
            "description": "ACMG score",
        }

        yield {
            "name": "count_hom",
            "type": "int",
            "category": "variants",
            "description": "Number of homozygous genotypes (1/1)",
        }
        yield {
            "name": "count_het",
            "type": "int",
            "category": "variants",
            "description": "Number of heterozygous genotypes (0/1)",
        }
        yield {
            "name": "count_ref",
            "type": "int",
            "category": "variants",
            "description": "Number of homozygous genotypes (0/0)",
        }
        yield {
            "name": "count_var",
            "type": "int",
            "category": "variants",
            "description": "Number of variants (not 0/0)",
        }

        yield {
            "name": "is_indel",
            "type": "bool",
            "category": "variants",
            "description": "True if variant is an indel",
        }

        yield {
            "name": "is_snp",
            "type": "bool",
            "category": "variants",
            "description": "True if variant is a snp",
        }

        yield {
            "name": "annotation_count",
            "type": "int",
            "category": "variants",
            "description": "Count of transcripts per variant",
        }

        yield {
            "name": "case_count_hom",
            "type": "int",
            "category": "variants",
            "description": "Number of homozygous genotypes (1/1) in case",
        }

        yield {
            "name": "case_count_het",
            "type": "int",
            "category": "variants",
            "description": "Number of heterozygous genotypes (1/0) in case",
        }

        yield {
            "name": "case_count_ref",
            "type": "int",
            "category": "variants",
            "description": "Number of homozygous genotypes (0/0) in case",
        }

        yield {
            "name": "control_count_hom",
            "type": "int",
            "category": "variants",
            "description": "Number of homozygous genotypes (1/1) in control",
        }

        yield {
            "name": "control_count_het",
            "type": "int",
            "category": "variants",
            "description": "Number of heterozygous genotypes (1/0) in control",
        }

        yield {
            "name": "control_count_ref",
            "type": "int",
            "category": "variants",
            "description": "Number of homozygous genotypes (0/0) in control",
        }

        # avoid duplicates fields ...
        duplicates = set()
        for field in self.get_fields():

            if field["name"] not in duplicates:
                yield field

            duplicates.add(field["name"])

    def get_extra_variants(self, **kwargs):
        """Yield variants with extra information computed.

        The following information are added. See get_extra_fields

        - favorite (bool): (Default: False)
        - comment (str): (Default: "")
        - classification (int): ACMG score (Default: 3 (uncertain significance)
        - count_var (int): Number of variants (not 0/0)
        - count_hom (int): How many variants are mutant homozygous within samples
        - count_het (int): How many variants are heterozygous within samples
        - count_ref (int): How many variants are wild homozygous with samples
        - is_indel (bool): Is the variation an insertion / deletion
        - is_snp (bool): Is the variation an single nucleotide variation

        If case/control are available from a pedfile, counting from case and
        control is also computed.
        In this case, it is necessary to give sample names in "case" and
        "control" keys in kwargs .

        Example of supported kwargs::

            {
                "case": ["boby", "raymond"],
                "control": ["lucas", "pierre"]
            }

        - case_count_hom (int): How many variants are mutant homozygous within case samples
        - case_count_het (int): How many variants are heterozygous within case samples
        - case_count_ref (int): How many variants are wild heterozygous within case samples
        - control_count_hom (int): How many variants are mutant homozygous within control samples
        - control_count_het (int): How many variants are heterozygous within control samples
        - control_count_ref (int): How many variants are wild heterozygous within control samples

        See Also:
            `cutevariant.core.reader.vcfreader.VcfReader.parse_variants`

        Args:
            **kwargs (optional): case and control sample names

        Yields:
            (generator[dict]): variants. See also: :meth:`get_variants`.

        Raises:
            AssertionError: If sample(s) are both in cases and controls.
        """
        case_and_control_samples_found = False
        if "case" in kwargs and "control" in kwargs:
            # Samples can't be both in cases and controls
            case_samples = kwargs["case"]
            control_samples = kwargs["control"]
            assert not set(case_samples) & set(control_samples), \
                "Found sample both in cases and controls!"
            case_and_control_samples_found = True

        for variant in self.get_variants():
            variant["favorite"] = False
            variant["comment"] = ""
            variant["classification"] = 3

            # For now set the first annotation as a major transcripts
            if "annotations" in variant:
                variant["annotation_count"] = len(variant["annotations"])

            # Count genotype by control and case
            genotype_counter = Counter()
            if "samples" in variant:
                for sample in variant["samples"]:
                    genotype_counter[sample["gt"]] += 1

            variant["count_hom"] = genotype_counter[2]
            variant["count_het"] = genotype_counter[1]
            variant["count_ref"] = genotype_counter[0]
            # Number of variants (not 0/0)
            variant["count_var"] = genotype_counter[1] + genotype_counter[2]

            variant["is_indel"] = len(variant["ref"]) != len(variant["alt"])
            variant["is_snp"] = len(variant["ref"]) == len(variant["alt"])

            # Count genotype by control and case
            if case_and_control_samples_found:

                case_counter = Counter()
                control_counter = Counter()

                if "samples" in variant:
                    # Note: No garantee that samples from DB are all qualified
                    # by PED data.
                    # So some samples from variants may not be in case/control samples.
                    for sample in variant["samples"]:
                        if sample["name"] in case_samples:
                            case_counter[sample["gt"]] += 1

                        elif sample["name"] in control_samples:
                            control_counter[sample["gt"]] += 1

                variant["case_count_hom"] = case_counter[2]
                variant["case_count_het"] = case_counter[1]
                variant["case_count_ref"] = case_counter[0]

                variant["control_count_hom"] = control_counter[2]
                variant["control_count_het"] = control_counter[1]
                variant["control_count_ref"] = control_counter[0]

            yield variant

    def get_extra_fields_by_category(self, category: str):
        """Syntaxic suggar to get fields according their category

        :param category can be usually variants, samples, annotations
        :return: A generator of fields
        :rtype: <generator>
        """
        return (
            field for field in self.get_extra_fields() if field["category"] == category
        )

    def get_fields_by_category(self, category: str):
        """Syntaxic suggar to get fields according their category

        :param category can be usually variants, samples, annotations
        :return: A generator of fields
        :rtype: <generator>
        """
        return (field for field in self.get_fields() if field["category"] == category)

    def get_variants_count(self) -> int:
        """Get variant count from the device

        Override this method to make it faster
        """
        return len(tuple(self.get_variants()))

    def get_total_file_size(self) -> int:
        """Compute file size int bytes"""
        # FakeReader is used ?
        if not self.device:
            return 0

        filename = self.device.name

        if cm.is_gz_file(filename):
            return cm.get_uncompressed_size(filename)
        # Go to EOF and get position in bytes
        size = self.device.seek(0, 2)
        # Rewind the file
        self.device.seek(0)
        return size

    def compute_number_lines(self):
        """Get a sample of lines in file if possible and if the end of file is
        not reached compute an evaluation of the global number of lines.

        Returns:
            Nothing but sets `self.number_lines` attribute.
        """

        def find_lines_in_text_file(text_file_handler):
            """Get first 15000 lines

            PS: don't care of headers (# lines), the influence is marginal on big
            files and also on small files (so quick to insert that the wrong number
            of lines is invisible).
            """
            first_lines = []
            for _ in range(15000):
                try:
                    first_lines.append(len(next(text_file_handler)))
                except StopIteration:
                    # EOF: exact number of lines is known
                    self.number_lines = len(first_lines)
                    break

            if self.number_lines is None:
                self.number_lines = int(
                    self.file_size / (sum(first_lines) / len(first_lines))
                )

            LOGGER.debug(
                "nb lines evaluated: %s; size: %s; lines used: %s",
                self.number_lines,
                self.file_size,
                len(first_lines),
            )

        # FakeReader is used ?
        if not self.device:
            return 0

        # Detect type of file handler
        if isinstance(self.device, (io.RawIOBase, io.BufferedIOBase)):
            # Binary opened file => assert that it is a vcf.gz file
            with gzip.open(self.device.name, "rb") as file_obj:
                find_lines_in_text_file(file_obj)
        elif isinstance(self.device, io.TextIOBase):
            find_lines_in_text_file(self.device)
        else:
            LOGGER.error("Unknown file handler type: %s", type(self.device))
            raise TypeError("Unknown file handler type: %s" % type(self.device))

        # Rewind the file
        self.device.seek(0)


def check_variant_schema(variant: dict):
    """Test if get_variant returns well formated nested data.

    This method is for testing purpose. It raises an exception if data is corrupted

    :param variant dict returned by AbstractReader.get_variant()

    """
    try:
        from schema import Schema, And, Or, Use, Optional, Regex
    except ImportError as e:
        LOGGER.warning("You should install optional package 'schema' via:")
        LOGGER.warning("\t - pypi: pip install cutevariant[dev]")
        LOGGER.warning("\t - git repo in editable mode: pip -e . [dev]")
        raise e

    checker = Schema(
        {
            "chr": And(Use(str.lower), str),
            "pos": int,
            "ref": And(Use(str.upper), Regex(r"^[ACGTN]+")),
            "alt": And(Use(str.upper), Regex(r"^[ACGTN]+")),
            Optional(str): Or(int, str, bool, float, None),
            Optional("annotations"): [
                {
                    "gene": str,
                    "transcript": str,
                    Optional(str): Or(int, str, bool, float),
                }
            ],
            Optional("samples"): [
                {
                    "name": str,
                    "gt": And(int, lambda x: x in [-1, 0, 1, 2]),
                    Optional(str): Or(int, str, bool, float),
                }
            ],
        }
    )

    checker.validate(variant)


def check_field_schema(field: dict):
    """Test if get_field returns well formated data

    This method is for testing purpose. It raises an exception if data is corrupted

    :param field dict returned by AbstractReader.get_field()
    """
    try:
        from schema import Schema, And, Use, Optional
    except ImportError as e:
        LOGGER.warning("You should install optional package 'schema' via:")
        LOGGER.warning("\t - pypi: pip install cutevariant[dev]")
        LOGGER.warning("\t - git repo in editable mode: pip -e . [dev]")
        raise e

    checker = Schema(
        {
            "name": And(str, Use(str.lower)),
            "type": lambda x: x in ["str", "int", "bool", "float"],
            "category": lambda x: x in ["variants", "annotations", "samples"],
            "description": str,
            Optional("constraint", default="NULL"): str,
        }
    )

    checker.validate(field)


def sanitize_field_name(field: str):
    # TODO
    LOGGER.warning("NOT implemented function!!")
    return field
