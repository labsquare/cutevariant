import sqlite3
import typing

from docxtpl import DocxTemplate

from cutevariant.config import Config
from cutevariant.core import sql
from cutevariant import constants


class AbstractReport():
    def __init__(self, conn: sqlite3.Connection):
        self._template = None
        self._conn = conn
        self._report_data = {}
    
    def set_template(self, template: str):
        self._template = template

    def get_template(self):
        return self._template

    def _set_data(self):
        raise NotImplementedError()

    def _get_data(self):
        return self._report_data

    def create(self, output_path):
        raise NotImplementedError()


class SampleReport(AbstractReport):
    def __init__(self, conn: sqlite3.Connection, sample_id: int):
        self._conn = conn
        self._sample_id = sample_id
        self._variant_classif_threshold = 1
        self._template = "examples/sample_report_template01.docx" #TODO: add to settings
        self._report_data = {}

    def set_variant_classif_threshold(self, threshold: int):
        self._variant_classif_threshold = threshold

    def get_sample(self):
        sample = sql.get_sample(self._conn, self._sample_id)
        if constants.HAS_OPERATOR in sample["tags"]:
            sample["tags"] = sample["tags"].split(constants.HAS_OPERATOR)
        else:
            sample["tags"] = [sample["tags"]]

        sample_classifs = self._classif_number_to_label("samples")
        sample["classification"] = sample_classifs.get(sample["classification"], sample["classification"])

        self._report_data["sample"] = sample

    def get_stats(self):

        ##total variants per genotype
        var_per_gt = {
            "title" : "Total variants per genotype",
            "header": ["Genotype", "Total"],
            "data" : []
        }
        number_to_gt = {0: "0/0", 1: "0/1", 2: "1/1"}
        for row in sql.get_variant_groupby_for_samples(self._conn, "gt", [self._sample_id]):
            row = [number_to_gt[row["gt"]], row["count"]]
            var_per_gt["data"].append(row)

        self._report_data["var_per_gt"] = var_per_gt


        ## total variants per variant classification
        var_per_var_classif = {
            "title" : "Total variants per variant classification",
            "header": ["Classification", "Total"],
            "data" : []
        }
        variant_classifs = self._classif_number_to_label("variants")
        for row in sql.get_variant_as_group(self._conn, "classification", sql.get_table_columns(self._conn, "variants"), "variants", {}):
            #if classif is not defined in config, keep the number by default
            row = [ variant_classifs.get(row["classification"], row["classification"]), 
                    row["count"]
                ]
            var_per_var_classif["data"].append(row)

        var_per_var_classif["data"] = sorted(var_per_var_classif["data"], key=lambda x: x[0])
        self._report_data["var_per_var_classif"] = var_per_var_classif


        ## total variants per genotype classification
        var_per_gt_classif = {
            "title" : "Total variants per genotype classification",
            "header": ["Classification", "Total"],
            "data" : []
        }
        genotypes_classifs = self._classif_number_to_label("genotypes")
        for row in sql.get_variant_groupby_for_samples(self._conn, "genotypes.classification", [self._sample_id]):
            row = [genotypes_classifs.get(row["classification"], row["classification"]), 
                    row["count"]
                ]
            var_per_gt_classif["data"].append(row)
        
        self._report_data["var_per_gt_classif"] = var_per_gt_classif

    def get_variants(self):
        self._report_data["classification_threshold"] = self._variant_classif_threshold

        config = Config("variables") or {}
        variant_name_pattern = config.get("variant_name_pattern") or "{chr}:{pos} - {ref}>{alt}"
        variant_name_pattern = variant_name_pattern.replace("ann.", "annotations___")
        
        variants_ids = sql.get_variants(self._conn, 
                                    ["id"],
                                    "variants",
                                    {"$and": [{"samples." + self._report_data["sample"]["name"] + ".classification": {"$gte": self._variant_classif_threshold}}]}
                                    )
        variants = []
        for id in variants_ids:
            id = id["id"]
            var = sql.get_variant(self._conn, id, with_samples=True)
            var["samples"] = [s for s in var["samples"] if s["sample_id"] == self._sample_id][0] #keep only current sample
            var["variant_name"] = variant_name_pattern.format(**var)
            variants.append(var)

        self._report_data["variants"] = variants

    def _classif_number_to_label(self, classification_type):
        """Create a dic to convert from classification number to label, based on Config values
        Args:
            classif_config (list): classification of interest in config. Ex: Config("classifications")["variants"]
        Returns:
            dict: {<classif number1> : <classif label1>, ...}
        Examples:

        >>> _classif_number_to_label([{'color': '#ff5500', 'description': '', 'name': 'Likely Pathogenic', 'number': 4}, {'color': '#b7b7b8', 'description': '', 'name': 'VSI', 'number': 3}])
        {"4": "Likely Pathogenic", "3": "VSI"}
        """
        config = Config("classifications").get(classification_type)

        dic = {}
        for c in config:
            dic[c["number"]] = c["name"]
        if 0 not in dic.keys(): #default classif for new variants, has to be defined if not in config
            dic[0] = "Unassigned (0)"
        return dic

    def _set_data(self):
        self.get_sample()
        self.get_stats()
        self.get_variants()

    def create(self, template_path: str, output_path: str):
        doc = DocxTemplate(template_path)
        self._set_data()
        for v in r._get_data()["variants"]:
            print(v)
        doc.render(self._get_data())
        doc.save(output_path)


if __name__ == "__main__":
    from cutevariant.core import sql

    # conn = sql.get_sql_connection("/home/sacha/exome/exome.db")
    conn = sql.get_sql_connection(
        "L:/Archives/NGS/BIO_INFO/BIO_INFO_Sam/scripts/cutevariant_project/devel_june2022.db"
    )
    # template = "L:/Archives/NGS/BIO_INFO/BIO_INFO_Sam/scripts/cutevariant_project/my_word_template.docx"
    # output = "L:/Archives/NGS/BIO_INFO/BIO_INFO_Sam/scripts/cutevariant_project/report.docx"
    template = "examples/sample_report_template01.docx"
    output = "examples/sample_report01.docx"

    r = SampleReport(conn, 2)
    r.create(template, output)
