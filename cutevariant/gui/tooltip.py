"""
Function to build tooltip 
Code needs improvement . Avoid multiple embbeded if 
"""
import re
import sqlite3
import textwrap

from cutevariant.config import Config
from cutevariant.gui import style as Style
from cutevariant.core import sql
from cutevariant import constants as cst
from cutevariant import commons as cm


NO_TAG_TEXT = "<i>no tags</i>"
NO_COMMENT_TEXT = "<i>no comment</i>"
TEXTWRAP_WIDTH = 60
TEXTWRAP_HOLDER = "..."


def genotype_tooltip(data: dict, conn: sqlite3.Connection):

    fields = [f["name"] for f in sql.get_field_by_category(conn, "samples")]
    sample = data.get("name", None)
    variant_id = data.get("variant_id", None)

    # extract all info for one sample
    genotype = {}
    if not variant_id or not sample:
        return "No genotype"
    else:
        genotype = next(sql.get_genotypes(conn, variant_id, fields, [sample]))

        # get fields description
        fields_description = {}
        for f in sql.get_fields(conn):
            field_name_prefix = ""
            field_name_prefix = (
                f.get("category", "")
                .replace("annotations", "ann.")
                .replace("samples", "samples.")
                .replace("variants", "")
            )
            fields_description[field_name_prefix + f.get("name")] = f.get(
                "description", f.get("name")
            )

        # all genotype values
        genotype_values_text = ""
        for f in genotype:
            v = genotype[f]
            if f not in [
                "sample_id",
                "variant_id",
                "name",
                "gt",
                "classification",
                "tags",
                "comment",
            ]:
                f_desc = fields_description.get("samples." + f, "unknown")
                f_desc = textwrap.shorten(f_desc, width=TEXTWRAP_WIDTH, placeholder=TEXTWRAP_HOLDER)
                genotype_values_text += f"<tr><td>{f}</td><td width='20'></td><td>{v}</td><td width='20'></td><td><small>{f_desc}</small></td></tr>"
        genotype["genotype_values_text"] = genotype_values_text

        # classification
        config = Config("classifications")
        classifications = config.get("genotypes", [])
        classification = genotype.get("classification", 0)
        classification_text = ""
        classification_color = ""
        style = None
        for i in classifications:
            if i["number"] == classification:
                style = i
                classification_text = style.get("name", "error")
                classification_desc = style.get("description", "")
                classification_color = style.get("color", "")
                # classification text
                classification_text += f" (" + classification_desc + ")"
        # add to data
        genotype["classification_text"] = classification_text
        genotype["classification_color"] = classification_color

        # Get variant name
        variant_name = cm.find_variant_name(conn=conn, variant_id=variant_id, troncate=False)

        genotype["variant_name"] = variant_name

        # tag genotype
        genotype["genotype_text"] = cst.GENOTYPE_DESC.get(int(genotype.get("gt", -1)), "unknown")

        # tags text
        genotype["tags_text"] = (
            genotype.get("tags", "").replace(cst.HAS_OPERATOR, "<br>") or NO_TAG_TEXT
        )

        # comment text
        genotype["comment_text"] = (
            genotype.get("comment", "").replace("\n", "<br>") or NO_COMMENT_TEXT
        )

        # Genotype tooltip
        tooltip = """
            <table>
                <tr><td>Genotype</td><td width='0'></td><td><b>{genotype_text}</b></td></tr> 
            </table>
            <hr>
            """.format(
            **genotype
        )

        # Classification toolTip
        tooltip += """
            <table>
                <tr><td>Classification</td><td width='20'></td><td style='color:{classification_color}'>{classification_text}</td></tr> 
                <tr><td>Tags</td><td width='20'></td><td>{tags_text}</td></tr> 
                <tr><td>Comment</td><td width='20'></td><td>{comment_text}</td></tr> 
            </table>
            <hr>
            <table>
                {genotype_values_text}
            </table>
            """.format(
            **genotype
        )

        tooltip_variant = variant_tooltip(dict(data), conn, counts=False, freqs=True)
        if tooltip_variant:
            tooltip += "<hr><hr>" + tooltip_variant

        tooltip_sample = sample_tooltip(dict(data), conn)
        if tooltip_sample:
            tooltip += "<hr><hr>" + tooltip_sample

        return tooltip


def sample_tooltip(data: dict, conn: sqlite3.Connection, genotype_classification: bool = False):

    tooltip = ""

    sample = data

    # if id come from genotype add sample_id
    if "id" not in sample and "sample_id" in sample:
        sample["id"] = sample["sample_id"]
        sample = dict(sql.get_sample(conn=conn, sample_id=sample["id"]))

    # if "name" in sample:
    #     if sample["name"]:
    name = sample.get("name", "error")
    tooltip += f"Sample <b>{name}</b><hr>"

    # Sample classification
    config = Config("classifications")
    sample_classifications = config.get("samples", [])

    # genotype classification
    nb_validation_genotype_message = ""
    # if genotype_classification:
    #     config = Config("classifications")
    #     genotype_classifications = config.get("genotypes", [])
    #     sample_id = sample["id"]
    #     sample_nb_genotype_by_classification = sql.get_sample_nb_genotype_by_classification(
    #         conn, sample_id
    #     )
    #     nb_validated_genotype = 0
    #     nb_validation_genotype_message = ""
    #     for classification in sample_nb_genotype_by_classification:
    #         nb_validation_genotype_text = ""
    #         nb_validation_genotype_color = ""
    #         nb_genotype_by_classification = sample_nb_genotype_by_classification[
    #             classification
    #         ]
    #         if classification > 0:
    #             nb_validated_genotype += nb_genotype_by_classification
    #         style = None
    #         for i in genotype_classifications:
    #             if i["number"] == classification:
    #                 style = i
    #         if style:
    #             if "name" in style:
    #                 nb_validation_genotype_text += style["name"]
    #                 if "description" in style:
    #                     nb_validation_genotype_text += (
    #                         f" (" + style["description"].strip() + ")"
    #                     )
    #             if "color" in style:
    #                 nb_validation_genotype_color = style["color"]
    #         nb_validation_genotype_message += f"<tr><td style='color:{nb_validation_genotype_color}' align='right'>{nb_genotype_by_classification}</td><td width='10'></td><td>{nb_validation_genotype_text}</td></tr>"
    #     if nb_validation_genotype_message:
    #         nb_validation_genotype_message = f"""
    #             <hr>
    #             Genotypes classification
    #             <table>
    #                 {nb_validation_genotype_message}
    #             </table>
    #         """

    sample_fields_mapping = {
        "count_validation_positive_variant": "validated variants",
        "count_validation_negative_variant": "rejected variants",
    }

    info_all_fields = ""
    info_classification = ""
    for sample_field in sample:
        sample_field_value = str(sample[sample_field]).replace("\n", "<br>")
        sample_field_value_color = ""

        # all fields
        if sample_field not in ["id", "name", "classification", "tags", "comment"]:
            if sample_field == "phenotype":
                sample_field_value = cst.PHENOTYPE_DESC.get(int(sample[sample_field]), "Unknown")
            elif sample_field == "sex":
                sample_field_value = cst.SEX_DESC.get(int(sample[sample_field]), "Unknown")
            sample_fields_mapping.get(sample_field, sample_field)
            sample_field = re.sub("_id$", "", sample_field)
            info_all_fields += f"<tr><td>{sample_field}</td><td width='20'></td><td style='color:{sample_field_value_color}'>{sample_field_value}</td></tr>"
        # classification fields
        elif sample_field in ["classification", "tags", "comment"]:
            if sample_field == "tags":
                sample_field_value = (
                    sample_field_value.replace(cst.HAS_OPERATOR, "<br>") or NO_TAG_TEXT
                )
            elif sample_field == "comment":
                sample_field_value = sample_field_value or NO_COMMENT_TEXT
            elif sample_field == "classification":
                if sample_field_value:
                    for i in sample_classifications:
                        if i["number"] == sample[sample_field]:
                            style = i
                            sample_field_value_name = style.get("name", "error")
                            sample_field_value_description = style.get("description", "")
                            sample_field_value_color = style.get("color", "")
                            sample_field_value = (
                                f"{sample_field_value_name} ({sample_field_value_description})"
                            )
                else:
                    sample_field_value = "<i>no classification</i>"

            info_classification += f"<tr><td>{sample_field}</td><td width='20'></td><td style='color:{sample_field_value_color}'>{sample_field_value}</td></tr>"

    tooltip += f"""
        <table>
            {info_classification}
        </table>
        <hr>
        <table>
            {info_all_fields}
        </table>
        {nb_validation_genotype_message}
    """
    tooltip += f"</table>"

    return tooltip


COUNTS_DESC = {"count_var": "number of occurence"}


def variant_tooltip(
    data: dict,
    conn: sqlite3.Connection,
    fields: list = None,
    counts: bool = True,
    freqs: bool = True,
):

    tooltip = ""  # str(data)

    variant = data

    # if id come from genotype ad variant_id
    if "id" not in variant and "variant_id" in variant:
        variant["id"] = variant["variant_id"]
        variant = variant | dict(
            sql.get_variant(
                conn=conn, variant_id=variant["id"], with_annotations=True, with_samples=True
            )
        )

    # get fields description
    fields_description = {}
    for f in sql.get_fields(conn):
        field_name_prefix = ""
        field_name_prefix = (
            f.get("category", "")
            .replace("annotations", "ann.")
            .replace("samples", "samples.")
            .replace("variants", "")
        )
        fields_description[field_name_prefix + f.get("name")] = f.get("description", f.get("name"))

    # get varant classification
    config = Config("classifications")
    variant_classifications = config.get("variants", [])

    # Get variant name
    variant_name = cm.find_variant_name(conn=conn, variant_id=variant.get("id", 0), troncate=False)

    # variant name
    if variant_name:
        tooltip += f"Variant <b>{variant_name}</b>"

    # variant classification
    message_variant_classification = "<table>"

    # variant current infos in selected fields
    message_variant_current_infos = None
    if fields:
        message_variant_current_infos = "<table>"
        for field in fields:
            f_desc = "unknown"
            if field.startswith("samples."):
                k = field.split(".")
                genotype_field = k[2]
                genotype_sample_name = k[1]
                if genotype_field == "gt":
                    if variant[field] is None:
                        value_gt = -1
                    else:
                        value_gt = int(variant[field])
                    # value = cst.GENOTYPE.get(value_gt)["name"]
                    value = cst.GENOTYPE_DESC.get(value_gt, "unknown")
                else:
                    value = variant[field]
                # f_desc = f"Genotype ({genotype_field}) for sample '{genotype_sample_name}'"
                f_desc = fields_description.get("samples." + genotype_field, f_desc)
            # elif field.startswith("ann."):
            #     k = field.split(".")
            #     ann_field = k[1]
            #     f_desc = fields_description.get(ann_field, f_desc)
            else:
                value = str(variant[field]).replace(cst.HAS_OPERATOR, "<br>")
            f_desc = fields_description.get(field, f_desc)
            f_desc = textwrap.shorten(f_desc, width=TEXTWRAP_WIDTH, placeholder=TEXTWRAP_HOLDER)
            message_variant_current_infos += f"<tr><td>{field}</td><td width='20'></td><td>{value}</td><td width='20'></td><td><small>{f_desc}</small></td></tr>"
        message_variant_current_infos += "</table>"

    # variant count and freq and classification
    message_variant_counts = ""
    message_variant_freqs = ""
    message_variant_counts_freqs = "<table>"
    message_variant_classification = "<table>"
    for field in variant:
        value = variant[field]
        value_color = ""
        if field.startswith("count_") and counts:
            field_desc = fields_description[field]
            field_desc = textwrap.shorten(
                field_desc, width=TEXTWRAP_WIDTH, placeholder=TEXTWRAP_HOLDER
            )
            message_variant_counts += f"<tr><td>{field}</td><td width='20'></td><td>{value}</td><td width='20'></td><td><small>{field_desc}</small></td></tr>"
        elif field.startswith("freq_") and freqs:
            # field = "database frequency"
            field_desc = fields_description.get(field, "unknown")
            field_desc = textwrap.shorten(
                field_desc, width=TEXTWRAP_WIDTH, placeholder=TEXTWRAP_HOLDER
            )
            value = str(value * 100) + "%"
            message_variant_freqs += f"<tr><td>{field}</td><td width='20'></td><td>{value}</td><td width='20'></td><td><small>{field_desc}</small></td></tr>"
        elif field in ["classification", "tags", "comment"]:
            if field == "tags":
                if value:
                    value = value.replace(cst.HAS_OPERATOR, "<br>")
                else:
                    value = NO_TAG_TEXT
            elif field == "comment":
                if not value:
                    value = NO_COMMENT_TEXT
                else:
                    value = value.replace("\n", "<br>")
            elif field == "classification":
                # value = "" #str(value)
                style = None
                for i in variant_classifications:
                    if i["number"] == variant[field]:
                        style = i
                        value_name = style.get("name", "")
                        value_description = (
                            style.get("description", "").strip().replace("\n", "<br>")
                        )
                        value_color = style.get("color", "")
                        value = f"{value_name} ({value_description})"
                # if style:
                #     if "name" in style:
                #         value += style["name"]
                #         if "description" in style:
                #             value += (
                #                 f" (" + style["description"].strip().replace("\n","<br>") + ")"
                #             )
                #     if "color" in style:
                #         value_color = style["color"]
            message_variant_classification += f"<tr><td>{field}</td><td width='20'></td><td style='color:{value_color}'>{value}</td></tr>"
    message_variant_classification += "</table>"
    message_variant_counts_freqs += f"{message_variant_counts}{message_variant_freqs}</table>"

    # final message
    tooltip += f"""<hr>{message_variant_classification}"""
    if message_variant_current_infos:
        tooltip += f"""<hr>{message_variant_current_infos}"""
    tooltip += f"""<hr>{message_variant_counts_freqs}"""

    return tooltip
