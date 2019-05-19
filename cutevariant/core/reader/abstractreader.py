from abc import ABC, abstractclassmethod


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
        self.file_size = 0
        self.read_bytes = 0
        self.samples = []
        self.fields = tuple()

    @abstractclassmethod
    def get_variants(self):
        """Abstract method that must return variants as an iterable of dictionnaries.

        Mandatory fields:
        =================
        `chr`, `pos`, `ref`, `alt` are mandatory.
        :Example:
            [
                {"chr": "chr3","pos": 3244,"ref": "A","alt":"C"},
                {"chr": "chr4","pos": 3244,"ref": "A","alt":"C"},
                {"chr": "chr5","pos": 3244,"ref": "A","alt":"C"},
            ]

        Full fields:
        ============
       `annotations`, `samples` and other fields can be added.
        :Example:
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
                    {"name":"boby", "gt": 1, "field_n":"value_n"},
                    {"name":"kevin", "gt": 1, "field_n":"value_n"}
                ]
            },]

        :return: A generator of variants
        :rtype: <generator>
        """
        raise NotImplementedError(self.__class__.__name__)

    @abstractclassmethod
    def get_fields(self):
        """Abstract methodthat must return fields description defined from parse_variant output.

        You **must** define sqlite type for each field (text, integer, bool).

        This function should set the attribute `fields` because it is called
        several times during the import and it could be expensive to redo the
        parsing every time.

        This function is called a first time before variants insertion.

        Full output:
        ============
        [
        {"name": "chr", "type": "text", "category": "variant", "description": "description"},
        {"name": "pos", "type": "text", "category": "variant", "description": "description"},
        {"name": "ref", "type": "text", "category": "variant", "description": "description"},
        {"name": "alt", "type": "text", "category": "variant", "description": "description"},
        {"name": "field_n", "type": "text", "category": "variant", "description": "description"},
        {"name": "name", "type": "text", "category": "annotations", "samples": "description"},
        {"name": "gt", "type": "text", "category": "annotations", "samples": "description"}
        ]

        :return: A generator of fields
        :rtype: <generator>
       """
        raise NotImplementedError(self.__class__.__name__)

    def get_fields_by_category(self, category: str):
        """Syntaxic suggar to get fields according their category

        :param category can be usually variants, samples, annotations
        :return: A generator of fields
        :rtype: <generator>
        """
        return (field for field in self.get_fields() if field["category"] == category)

    def get_variants_count(self) -> int:
        """Get variant count from the device.
        Override this method to make it faster
        """
        return len(tuple(self.get_variants()))

    def get_samples(self) -> str:
        """Return list of samples.
        Override this method to have samples in sqlite database.
        """
        return self.samples

    def get_extra_fields(self):
        """Mandatory fields to add automatically

        ..todo: Move this methods somewhere else ..
        ..warning: DEPRECTATED
        """
        yield from self.parse_fields()
        yield {
            "name": "description",
            "type": "text",
            "category": "extra",
            "description": "description of variant",
        }
        yield {
            "name": "favoris",
            "type": "bool",
            "category": "extra",
            "description": "is favoris",
            "default": False,
        }


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
                {"name": str, "gt": And(int, lambda x: x in [-1, 0, 1, 2])}
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
