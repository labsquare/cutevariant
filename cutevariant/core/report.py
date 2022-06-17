import codecs
import datetime
import getpass
import jinja2
import os
import shutil
import sqlite3
import typing

from cutevariant.commons import recursive_overwrite
from cutevariant.config import Config
from cutevariant.core import sql
from cutevariant import constants


class AbstractReport:

    """
    Abstract class for all report generator

    """

    def __init__(self, conn: sqlite3.Connection):
        self._template = None
        self._conn = conn

    def set_template(self, template: str):
        """Set template path
        Args:
            template (str): Path to jinja2 template
        """
        self._template = template

    def get_data(self) -> dict:
        """Return data to inject into the template

        Raises:
            NotImplementedError
        """
        raise NotImplementedError()

    def create(self, output_path: str):
        """Create HTML report

        Args:
            output_path (str): output html path

        Raises:
            NotImplementedError
        """
        raise NotImplementedError()


class SampleReport(AbstractReport):

    """
    Create HTML report for a selected samples
    """

    def __init__(self, conn: sqlite3.Connection, sample_id: int):
        super().__init__(conn)
        self._sample_id = sample_id
        self._variant_classif_threshold = 1

    def set_variant_classif_threshold(self, threshold: int):
        self._variant_classif_threshold = threshold

    def get_sample(self) -> dict:
        """Return data from samples tables
        Returns:
            dict
        """
        sample = sql.get_sample(self._conn, self._sample_id)
        if constants.HAS_OPERATOR in sample["tags"]:
            sample["tags"] = sample["tags"].split(constants.HAS_OPERATOR)
        else:
            sample["tags"] = [sample["tags"]]

        sample_classifs = SampleReport._classif_number_to_label("samples")
        sample["classification"] = sample_classifs.get(
            sample["classification"], sample["classification"]
        )

        return sample

    def get_stats(self) -> dict:
        """Return variants stat of the current samples"""
        ##total variants per genotype
        var_per_gt = {
            "title": "Total variants per genotype",
            "header": ["Genotype", "Total"],
            "data": [],
        }
        number_to_gt = {0: "0/0", 1: "0/1", 2: "1/1"}
        for row in sql.get_variant_groupby_for_samples(self._conn, "gt", [self._sample_id]):
            row = [number_to_gt[row["gt"]], row["count"]]
            var_per_gt["data"].append(row)

        ## total variants per variant classification
        var_per_var_classif = {
            "title": "Total variants per variant classification",
            "header": ["Classification", "Total"],
            "data": [],
        }
        variant_classifs = SampleReport._classif_number_to_label("variants")
        for row in sql.get_variant_as_group(
            self._conn,
            "classification",
            sql.get_table_columns(self._conn, "variants"),
            "variants",
            {},
        ):
            # if classif is not defined in config, keep the number by default
            row = [variant_classifs.get(row["classification"], row["classification"]), row["count"]]
            var_per_var_classif["data"].append(row)

        var_per_var_classif["data"] = sorted(var_per_var_classif["data"], key=lambda x: x[0])

        ## total variants per genotype classification
        var_per_gt_classif = {
            "title": "Total variants per genotype classification",
            "header": ["Classification", "Total"],
            "data": [],
        }
        genotypes_classifs = SampleReport._classif_number_to_label("genotypes")
        for row in sql.get_variant_groupby_for_samples(
            self._conn, "genotypes.classification", [self._sample_id]
        ):
            row = [
                genotypes_classifs.get(row["classification"], row["classification"]),
                row["count"],
            ]
            var_per_gt_classif["data"].append(row)

        return {
            "var_per_gt": var_per_gt,
            "var_per_var_classif": var_per_var_classif,
            "var_per_gt_classif": var_per_gt_classif,
        }

    def get_variants(self) -> dict:
        """
        Return classified variants of the current samples
        """
        config = Config("variables") or {}
        variant_name_pattern = config.get("variant_name_pattern") or "{chr}:{pos} - {ref}>{alt}"
        variant_name_pattern = variant_name_pattern.replace("ann.", "annotations___")

        variants_ids = sql.get_variants(
            self._conn,
            ["id"],
            "variants",
            {
                "$and": [
                    {
                        "samples."
                        + sql.get_sample(self._conn, self._sample_id)["name"]
                        + ".classification": {"$gte": self._variant_classif_threshold}
                    }
                ]
            },
        )
        variants = []
        for var_id in variants_ids:
            var_id = var_id["id"]
            var = sql.get_variant(self._conn, var_id, with_samples=True)
            var["samples"] = [s for s in var["samples"] if s["sample_id"] == self._sample_id][
                0
            ]  # keep only current sample
            var["variant_name"] = variant_name_pattern.format(**var)
            variants.append(var)

        return variants

    @classmethod
    def _classif_number_to_label(cls, classification_type: list) -> dict:
        """Create a dic to convert from classification number to label, based on Config values
        Args:
            classif_config (list): classification of interest in config. Ex: Config("classifications")["variants"]
        Returns:
            dict: {<classif number1> : <classif label1>, ...}
        Examples:
            SampleReport._classif_number_to_label([{'color': '#ff5500', 'description': '', 'name': 'Likely Pathogenic', 'number': 4}, {'color': '#b7b7b8', 'description': '', 'name': 'VSI', 'number': 3}])
            {"4": "Likely Pathogenic", "3": "VSI"}
        """
        config = Config("classifications").get(classification_type)

        dic = {}
        for c in config:
            dic[c["number"]] = c["name"]
        if (
            0 not in dic.keys()
        ):  # default classif for new variants, has to be defined if not in config
            dic[0] = "Unassigned (0)"
        return dic

    def get_data(self) -> dict:
        """override from AbstractReport"""
        return {
            "date": datetime.datetime.today().strftime("%Y-%m-%d %H:%M:%S"),
            "user": getpass.getuser(),
            "sample": self.get_sample(),
            "stats": self.get_stats(),
            "classification_threshold": self._variant_classif_threshold,
            "variants": self.get_variants(),
        }

    def create(self, output_path: str):
        """override from AbstractReport"""
        if self._template is None:
            raise ValueError("No template is set ; use self.set_template(str)")

        template_dir = os.path.dirname(self._template)
        output_dir = os.path.dirname(output_path)

        env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(template_dir),
            autoescape=True,
            extensions=["jinja_markdown.MarkdownExtension"],
        )

        template = env.get_template(os.path.basename(self._template))
        output = template.render(self.get_data())

        # Dangereux ..
        # recursive_overwrite(template_dir, output_dir, ignore=shutil.ignore_patterns("*.html"))

        with codecs.open(output_path, "w", "utf-8") as f:
            f.write(output)


if __name__ == "__main__":
    from cutevariant.core import sql
    from cutevariant.commons import create_fake_conn

    # conn = sql.get_sql_connection(
    #     "L:/Archives/NGS/BIO_INFO/BIO_INFO_Sam/scripts/cutevariant_project/devel_june2022.db"
    # )
    conn = create_fake_conn()
    template = "examples/html_template/Template01.html"
    output = "examples/Report01.html"

    r = SampleReport(conn, 1)
    r.set_template(template)
    r.create(output)
