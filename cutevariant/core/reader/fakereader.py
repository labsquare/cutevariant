from .abstractreader import AbstractReader


class FakeReader(AbstractReader):
    def __init__(self):
        super().__init__(None)

    def get_variants(self):
        yield {
            "chr": "11",
            "pos": 125010,
            "ref": "T",
            "alt": "A",
            "annotations": [
                {"transcript": "NM_234234", "gene": "CFTR", "ref": "NN"},
                {"transcript": "NM_234235", "gene": "CFTR", "ref": "NN"},
            ],
            "samples": [{"name": "sacha", "gt": 1, "dp": 30}],
        }

        yield {
            "chr": "12",
            "pos": 125010,
            "ref": "T",
            "alt": "A",
            "annotations": [
                {"transcript": "NM_234234", "gene": "CFTR", "ref": "YY"},
                {"transcript": "NM_234235", "gene": "CFTR", "ref": "YY"},
            ],
            "samples": [{"name": "sacha", "gt": 1, "dp": 50}],
        }

        yield {
            "chr": "13",
            "pos": 125010,
            "ref": "T",
            "alt": "A",
            "annotations": [
                {"transcript": "NM_234234", "gene": "CFTR"},
                {"transcript": "NM_234235", "gene": "CFTR"},
            ],
            "samples": [{"name": "sacha", "gt": 1, "dp": 10}],
        }

    def get_fields(self):
        """Extract fields informations from VCF fields

        .. note:: Fields used in PRIMARY KEYS have the constraint NOT NULL.
            By default, all other fields can have NULL values.
        """

        yield {
            "name": "chr",
            "category": "variants",
            "description": "chromosom",
            "type": "str",
            "constraint": "NOT NULL",
        }
        yield {
            "name": "pos",
            "category": "variants",
            "description": "position",
            "type": "int",
            "constraint": "NOT NULL",
        }

        yield {
            "name": "ref",
            "category": "variants",
            "description": "reference base",
            "type": "str",
            "constraint": "NOT NULL",
        }
        yield {
            "name": "alt",
            "category": "variants",
            "description": "alternative base",
            "type": "str",
            "constraint": "NOT NULL",
        }

        yield {
            "name": "gt",
            "category": "samples",
            "description": "genotype",
            "type": "int",
        }

        yield {
            "name": "dp",
            "category": "samples",
            "description": "genotype depth",
            "type": "int",
        }

        yield {
            "name": "af",
            "category": "samples",
            "description": "allele frequency",
            "type": "float",
        }

        yield {
            "name": "gene",
            "category": "annotations",
            "description": "gene name",
            "type": "str",
        }

        yield {
            "name": "transcript",
            "category": "annotations",
            "description": "gene transcripts",
            "type": "str",
        }

        yield {
            "name": "ref",
            "category": "annotations",
            "description": "duplicate test",
            "type": "str",
        }

    def get_samples(self):
        return ["sacha"]
