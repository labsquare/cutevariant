from .abstractreader import AbstractReader
import gzip
import json
from cutevariant.commons import get_genotype_type


class NirvanaReader(AbstractReader):
    def __init__(self, filename):
        super().__init__(filename)

        self._header = {}
        self._read_header()

    def _read_header(self):

        with gzip.open(self.filename, "rt") as f:
            self._header = json.loads(next(f).strip()[10:-14])

    def get_variants(self):

        gene_section_line = '],"genes":['
        end_line = "]}"

        current_samples = self.get_samples()

        with gzip.open(self.filename, "rt") as f:

            next(f)  # Skip header

            for line in f:
                trim_line = line.strip()

                if trim_line == gene_section_line:
                    continue

                else:

                    if not trim_line.startswith("{"):
                        continue

                    raw_variant = json.loads(trim_line.rstrip(","))

                    if "variants" in raw_variant:
                        for v in raw_variant["variants"]:

                            variant = {
                                "chr": raw_variant["chromosome"],
                                "pos": raw_variant["position"],
                                "ref": v["refAllele"],
                                "alt": v["altAllele"],
                            }

                            # Add Annotations
                            variant["annotations"] = []

                            if "transcripts" in v:
                                for tx in v["transcripts"]:
                                    variant["annotations"].append(
                                        {"transcript": tx["transcript"], "gene": tx["hgnc"]}
                                    )

                            # Add genotypes
                            variant["samples"] = []

                            if "samples" in raw_variant:

                                for i, sample in enumerate(raw_variant["samples"]):

                                    name = current_samples[i]
                                    gt = get_genotype_type(sample.get("genotype"))

                                    variant["samples"].append(
                                        {"name": name, "gt": gt, "dp": sample.get("totalDepth", -1)}
                                    )

                            yield variant

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

    def get_samples(self):
        if "samples" in self._header:
            return self._header["samples"]

        return ["nirvana"]
