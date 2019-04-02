from .abstractreader import AbstractReader
import vcf


class FakeReader(AbstractReader):


    def __init__(self, device):
        super().__init__(device)

    def parse_variants(self):
        yield {
        "chr": "11",
        "pos": 125010,
        "ref": "T",
        "alt": "A",
        "samples": [{
            "name":"sacha",
            "gt": "1",
            "af": 0.3
            }]
        }

        yield {
        "chr": "12",
        "pos": 125010,
        "ref": "T",
        "alt": "A",
        "samples": [{
            "name":"sacha",
            "gt": "1",
            "af": 0.3
            }]
        }

        yield {
        "chr": "13",
        "pos": 125010,
        "ref": "T",
        "alt": "A",
        "samples": [{
            "name":"sacha",
            "gt": "1",
            "af": 0.3
            }]
        }

    def parse_fields(self):
        """ Extract fields informations from VCF fields """ 

        yield {
            "name": "chr",
            "category": "variant",
            "description": "chromosom",
            "type": "str"
        }
        yield {
            "name": "pos",
            "category": "variant",
            "description": "position",
            "type": "int"
        }

        yield {
            "name": "ref",
            "category": "variant",
            "description": "reference base",
            "type": "str"
        }
        yield {
            "name": "alt",
            "category": "variant",
            "description": "alternative base",
            "type": "str"
        }

        yield {
            "name": "gt",
            "category": "sample",
            "description": "genotype",
            "type": "int"
        }

        yield {
            "name": "af",
            "category": "sample",
            "description": "allele frequency",
            "type": "float"
        }


    def get_samples(self):
        return ["sacha"]
       