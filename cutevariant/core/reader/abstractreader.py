from abc import ABC, abstractmethod
import os
from collections import Counter
import cutevariant.commons as cm

LOGGER = cm.logger()


class AbstractReader(ABC):
    """Base class for all Readers required to import variants into the database.

    Subclass it if you want a new file parser .

    Attributes:

        device: a file object typically returned by open()
        file_size: file size in bytes
        read_bytes: current bytes readed (progression = read_bytes / file_size)
        samples: list of samples in the file (default: empty)

    Example:
        with open(filename,"r") as file:
            reader = Reader()
            reader.get_variants()
    """

    def __init__(self, device):
        super(AbstractReader, self).__init__()
        self.device = device

        self.file_size = self.compute_total_size()
        self.read_bytes = 0
        self.samples = list()

    @classmethod
    @abstractmethod
    def get_variants(cls):
        """Abstract method must return variants as an iterable of dictionnaries.

        Variant dictionnary has 4 mandatory fields `chr`, `pos`, `ref`, `alt`.
        Other fields are optionnal
        For instance:
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
                print(variant["chr"], variant["pos"])

        """
        raise NotImplementedError(cls.__class__.__name__)

    @classmethod
    @abstractmethod
    def get_fields(cls):
        """Abstract method hat must return fields description

        Full output:
        ============
        [
        {"name": "chr", "type": "text", "category": "variant", "description": "description"},
        {"name": "pos", "type": "text", "category": "variant", "description": "description"},
        {"name": "ref", "type": "text", "category": "variant", "description": "description"},
        {"name": "alt", "type": "text", "category": "variant", "description": "description"},
        {"name": "field_n", "type": "text", "category": "variant", "description": "description"},
        {"name": "name", "type": "text", "category": "annotations", "samples": "description"},
        {"name": "genotype", "type": "text", "category": "annotations", "samples": "description"}
        ]

        Yields:
            dict: field dictionnary

        Examples:
            >>> for field in reader.get_fields():
                    print(field["name"], field["description"])
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
            "description": "is favorite",
        }
        yield {
            "name": "comment",
            "type": "str",
            "category": "variants",
            "description": "Variant comment",
        }
        yield {
            "name": "classification",
            "type": "int",
            "category": "variants",
            "description": "ACMG score",
        }

        yield {
            "name": "is_major",
            "type": "bool",
            "category": "annotations",
            "description": "is a major transcript",
        }

        yield {
            "name": "count_hom",
            "type": "int",
            "category": "variants",
            "description": "Count number of homozygous genotypes (1/1)",
        }
        yield {
            "name": "count_het",
            "type": "int",
            "category": "variants",
            "description": "Count number of heterozygous genotypes (0/1)",
        }
        yield {
            "name": "count_ref",
            "type": "int",
            "category": "variants",
            "description": "Count number of homozygous genotypes (0/0)",
        }
        yield {
            "name": "count_var",
            "type": "int",
            "category": "variants",
            "description": "Count number of variant ( not 0/0)",
        }

        yield {
            "name": "is_indel",
            "type": "bool",
            "category": "variants",
            "description": "True is variant is an indel",
        }

        yield {
            "name": "is_snp",
            "type": "bool",
            "category": "variants",
            "description": "True is variant is a snp",
        }

        yield {
            "name": "annotation_count",
            "type": "int",
            "category": "variants",
            "description": "Transcript count per variants",
        }

        yield {
            "name": "case_count_hom",
            "type": "int",
            "category": "variants",
            "description": "Count number of homozygous genotypes (1/1) in case",
        }

        yield {
            "name": "case_count_het",
            "type": "int",
            "category": "variants",
            "description": "Count number of heterozygous genotypes (1/0) in case",
        }

        yield {
            "name": "case_count_ref",
            "type": "int",
            "category": "variants",
            "description": "Count number of homozygous ( 0/0) in case",
        }

        yield {
            "name": "control_count_hom",
            "type": "int",
            "category": "variants",
            "description": "Count number of homozygous genotypes (1/1) in control",
        }

        yield {
            "name": "control_count_het",
            "type": "int",
            "category": "variants",
            "description": "Count number of heterozygous genotypes (1/0) in control",
        }

        yield {
            "name": "control_count_ref",
            "type": "int",
            "category": "variants",
            "description": "Count number of homozygous (0/0) in control",
        }

        # yield {
        #     "name": "case_count_hom",
        #     "type": "int",
        #     "category": "variants",
        #     "description": "Count number of homozygous genotypes (1/1)",
        # }
        # yield {
        #     "name": "case_count_het",
        #     "type": "int",
        #     "category": "variants",
        #     "description": "Count number of heterozygous genotypes (0/1)",
        # }
        # yield {
        #     "name": "case_count_ref",
        #     "type": "int",
        #     "category": "variants",
        #     "description": "Count number of homozygous genotypes (0/0)",
        # }

        # yield {
        #     "name": "control_count_hom",
        #     "type": "int",
        #     "category": "variants",
        #     "description": "Count number of homozygous genotypes (1/1)",
        # }
        # yield {
        #     "name": "control_count_het",
        #     "type": "int",
        #     "category": "variants",
        #     "description": "Count number of heterozygous genotypes (0/1)",
        # }
        # yield {
        #     "name": "control_count_ref",
        #     "type": "int",
        #     "category": "variants",
        #     "description": "Count number of homozygous genotypes (0/0)",
        # }

        # avoid duplicates fields ...
        duplicates = set()
        for field in self.get_fields():

            if field["name"] not in duplicates:
                yield field

            duplicates.add(field["name"])

    def get_extra_variants(self, **kwargs):
        for variant in self.get_variants():
            variant["favorite"] = False
            variant["comment"] = ""
            variant["classification"] = 3

            # For now set the first annotation as a major transcripts
            if "annotations" in variant:
                variant["annotation_count"] = len(variant["annotations"])
                for index, ann in enumerate(variant["annotations"]):
                    if "is_major" not in ann:
                        if index == 0:
                            ann["is_major"] = True
                        else:
                            ann["is_major"] = False

            # Count genotype by control and case
            genotype_counter = Counter()
            if "samples" in variant:
                for sample in variant["samples"]:
                    genotype_counter[sample["gt"]] += 1

            variant["count_hom"] = genotype_counter[2]
            variant["count_het"] = genotype_counter[1]
            variant["count_ref"] = genotype_counter[0]
            variant["count_var"] = genotype_counter[1] + genotype_counter[2]

            variant["is_indel"] = len(variant["ref"]) != len(variant["alt"])
            variant["is_snp"] = len(variant["ref"]) == len(variant["alt"])

            # Count genotype by control and case
            if "case" in kwargs and "control" in kwargs:

                case_samples = kwargs["case"]
                control_samples = kwargs["control"]

                case_counter = Counter()
                control_counter = Counter()

                if "samples" in variant:
                    for sample in variant["samples"]:
                        if sample["name"] in case_samples:
                            case_counter[sample["gt"]] += 1

                        if sample["name"] in control_samples:
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

    def compute_total_size(self) -> int:
        """Compute file size int bytes"""
        if not self.device:
            return 0

        filename = self.device.name

        if cm.is_gz_file(filename):
            return cm.get_uncompressed_size(filename)
        return os.path.getsize(filename)


def check_variant_schema(variant: dict):
    """Test if get_variant returns well formated nested data.

    This method is for testing purpose. It raises an exception if data is corrupted

    :param variant dict returned by AbstractReader.get_variant()

    """
    try:
        from schema import Schema, And, Or, Use, Optional, Regex
    except ImportError as e:
        print("You should install optional package 'schema' via:")
        print("\t - pypi: pip install cutevariant[dev]")
        print("\t - git repo in editable mode: pip -e . [dev]")
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
        print("You should install optional package 'schema' via:")
        print("\t - pypi: pip install cutevariant[dev]")
        print("\t - git repo in editable mode: pip -e . [dev]")
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
