"""
Function to build tooltip 
Code needs improvement . Avoid multiple embbeded if 
"""
import sqlite3

from cutevariant.config import Config
from cutevariant.gui import style as Style
from cutevariant.core import sql
from cutevariant import constants as cst


def genotype_tooltip(data: dict, conn: sqlite3.Connection):

    fields = [f["name"] for f in sql.get_field_by_category(conn, "samples")]
    sample = data.get("name", None)
    variant_id = data.get("variant_id", None)

    # extract all info for one sample
    genotype = {}
    if variant_id and sample:
        genotype = next(sql.get_genotypes(conn, variant_id, fields, [sample]))
    else:
        return "No genotype"

    # Get variant_name_pattern
    config = Config("variables") or {}
    variant_name_pattern = (
        config.get("variant_name_pattern") or "{chr}:{pos} - {ref}>{alt}"
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
            # f_upper=f.upper()
            f_upper = f
            genotype_values_text += (
                f"<tr><td>{f_upper}</td><td width='20'></td><td>{v}</td></tr>"
            )
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
    if style:
        if "name" in style:
            classification_text += style["name"]
            if "description" in style:
                classification_text += f" (" + style["description"].strip() + ")"
        if "color" in style:
            classification_color = style["color"]
    genotype["classification_text"] = classification_text
    genotype["classification_color"] = classification_color

    # extract info from variant
    variant = sql.get_variant(conn, variant_id, with_annotations=True)
    if len(variant["annotations"]):
        for ann in variant["annotations"][0]:
            variant["annotations___" + str(ann)] = variant["annotations"][0][ann]
    variant_name_pattern = variant_name_pattern.replace("ann.", "annotations___")
    variant_name = variant_name_pattern.format(**variant)
    genotype["variant_name"] = variant_name

    # tag genotype
    if genotype["gt"]:
        genotype_text = Style.GENOTYPE.get(genotype["gt"], "Unknown")["name"]
    else:
        genotype_text = "<i>no tag</i>"
    genotype["genotype_text"] = genotype_text

    # tags text
    if genotype["tags"]:
        tags_text = genotype["tags"].replace(cst.HAS_OPERATOR, "<br>")
    else:
        tags_text = "<i>no tag</i>"
    genotype["tags_text"] = tags_text

    # comment text
    if genotype["comment"]:
        comment_text = genotype["comment"].replace("\n", "<br>")
    else:
        comment_text = "<i>no comment</i>"
    genotype["comment_text"] = comment_text

    # Message
    message = """
        <table>
            <tr><td>Sample</td><td width='0'></td><td><b>{name}</b></td></tr> 
            <tr><td>Variant</td><td width='0'></td><td><b>{variant_name}</b></td></tr> 
        </table>
        <hr>
        """.format(
        **genotype
    )
    if genotype["gt"]:
        message += """
        <table>
            <tr><td>gt</td><td width='20'></td><td>{genotype_text}</td></tr> 
            {genotype_values_text}
        </table>
        <hr>
        <table>
            <tr><td>Classification</td><td width='20'></td><td style='color:{classification_color}'>{classification_text}</td></tr> 
            <tr><td>Tags</td><td width='20'></td><td>{tags_text}</td></tr> 
            <tr><td>Comment</td><td width='20'></td><td>{comment_text}</td></tr> 
        </table>
        """.format(
            **genotype
        )
    else:
        message += """
        <table>
            <tr><td><i>no genotype</i></td></tr> 
        </table>
        """

    message_variant = None
    message_variant = variant_tooltip(
        dict(data), conn
    )
    if message_variant:
        message += "<hr><hr>" + message_variant

    return message


def sample_tooltip(data: dict, conn: sqlite3.Connection):

    info = ""
    sample = data
    if "name" in sample:
        if sample["name"]:
            name = sample["name"]
            info += f"Sample <b>{name}</b><hr>"

    # Sample classification
    config = Config("classifications")
    sample_classifications = config.get("samples", [])

    # genotype classification
    config = Config("classifications")
    genotype_classifications = config.get("genotypes", [])
    sample_id = sample["id"]
    sample_nb_genotype_by_classification = sql.get_sample_nb_genotype_by_classification(
        conn, sample_id
    )
    nb_validated_genotype = 0
    nb_validation_genotype_message = ""
    for classification in sample_nb_genotype_by_classification:
        nb_validation_genotype_text = ""
        nb_validation_genotype_color = ""
        nb_genotype_by_classification = sample_nb_genotype_by_classification[
            classification
        ]
        if classification > 0:
            nb_validated_genotype += nb_genotype_by_classification
        style = None
        for i in genotype_classifications:
            if i["number"] == classification:
                style = i
        if style:
            if "name" in style:
                nb_validation_genotype_text += style["name"]
                if "description" in style:
                    nb_validation_genotype_text += (
                        f" (" + style["description"].strip() + ")"
                    )
            if "color" in style:
                nb_validation_genotype_color = style["color"]
        nb_validation_genotype_message += f"<tr><td style='color:{nb_validation_genotype_color}' align='right'>{nb_genotype_by_classification}</td><td width='10'></td><td>{nb_validation_genotype_text}</td></tr>"
    if nb_validation_genotype_message:
        nb_validation_genotype_message = f"""
            <hr>
            Genotypes classification
            <table>
                {nb_validation_genotype_message}
            </table>
        """

    info_all_fields = ""
    info_classification = ""
    for sample_field in sample:
        sample_field_value = str(sample[sample_field]).replace("\n", "<br>")
        sample_field_value_color = ""
        # all fields
        if sample_field not in ["id", "name", "classification", "tags", "comment"]:
            if sample_field == "phenotype":
                sample_field_value = cst.PHENOTYPE_DESC.get(
                    int(sample[sample_field]), "Unknown"
                )
            if sample_field == "sex":
                sample_field_value = cst.SEX_DESC.get(
                    int(sample[sample_field]), "Unknown"
                )
            info_all_fields += f"<tr><td>{sample_field}</td><td width='20'></td><td style='color:{sample_field_value_color}'>{sample_field_value}</td></tr>"
        # classification fields
        if sample_field in ["classification", "tags", "comment"]:
            if sample_field == "tags":
                if sample_field_value:
                    sample_field_value = sample_field_value.replace(cst.HAS_OPERATOR, "<br>")
                else:
                    sample_field_value = "<i>no tag</i>"
            if sample_field == "comment":
                if not sample_field_value:
                    sample_field_value = "<i>no comment</i>"
            if sample_field == "classification":
                if sample_field_value:
                    sample_field_value = ""
                    style = None
                    for i in sample_classifications:
                        if i["number"] == sample[sample_field]:
                            style = i
                    if style:
                        if "name" in style:
                            sample_field_value += style["name"]
                            if "description" in style:
                                sample_field_value += (
                                    f" (" + style["description"].strip() + ")"
                                )
                        if "color" in style:
                            sample_field_value_color = style["color"]
                else:
                    sample_field_value = "<i>no classification</i>"
            info_classification += f"<tr><td>{sample_field}</td><td width='20'></td><td style='color:{sample_field_value_color}'>{sample_field_value}</td></tr>"
    info += f"""
        <table>
            {info_all_fields}
        </table>
        <hr>
        <table>
            {info_classification}
        </table>
        {nb_validation_genotype_message}
    """
    info += f"</table>"

    return info


def variant_tooltip(data: dict, conn: sqlite3.Connection, fields = None):

    message = "" #str(data)

    variant = data

    # if id come from genotype ad variant_id
    if "id" not in variant and "variant_id" in variant:
        variant["id"] = variant["variant_id"]
        variant = variant | dict(sql.get_variant(conn=conn, variant_id=variant["id"], with_annotations=True, with_samples=True))

    # Get variant_name_pattern
    config = Config("variables") or {}
    variant_name_pattern = (
        config.get("variant_name_pattern") or "{chr}:{pos} - {ref}>{alt}"
    )

    # get varant classification
    config = Config("classifications")
    variant_classifications = config.get("variants", [])

    # extract info from variant
    variant_for_pattern = variant
    if len(variant_for_pattern["annotations"]):
        for ann in variant_for_pattern["annotations"][0]:
            variant_for_pattern["annotations___" + str(ann)] = variant_for_pattern["annotations"][0][ann]
    variant_name_pattern = variant_name_pattern.replace("ann.", "annotations___")
    variant_name = variant_name_pattern.format(**variant_for_pattern)

    # variant name
    if variant_name:
        message += f"Variant <b>{variant_name}</b>"

    # variant classification
    message_variant_classification = "<table>"
    

    # variant current infos in selected fields
    message_variant_current_infos = None
    if fields:
        message_variant_current_infos = "<table>"
        for field in fields:
            if field.startswith("samples."):
                k = field.split(".")
                if k[2] == "gt":
                    if variant[field] is None:
                        value_gt = -1
                    else:
                        value_gt = int(variant[field])
                    value = Style.GENOTYPE.get(value_gt)["name"]
                else:
                    value = variant[field]
            else:
                value = str(variant[field]).replace(cst.HAS_OPERATOR,"<br>")
            message_variant_current_infos += f"<tr><td>{field}</td><td width='20'></td><td>{value}</td></tr>"
        message_variant_current_infos += "</table>"

    # variant count and freq and classification
    message_variant_counts = ""
    message_variant_freqs = ""
    message_variant_counts_freqs = "<table>"
    message_variant_classification = "<table>"
    for field in variant:
        value = variant[field]
        value_color = ""
        if field.startswith("count_"):
            message_variant_counts += f"<tr><td>{field}</td><td width='20'></td><td>{value}</td></tr>"
        elif field.startswith("freq_"):
            message_variant_freqs += f"<tr><td>{field}</td><td width='20'></td><td>{value}</td></tr>"
        elif field in ["classification", "tags", "comment"]:
            if field == "tags":
                if value:
                    value = value.replace(cst.HAS_OPERATOR, "<br>")
                else:
                    value = "<i>no tag</i>"
            if field == "comment":
                if not value:
                    value = "<i>no comment</i>"
                else:
                    value = value.replace("\n","<br>")
            if field == "classification":
                value = "" #str(value)
                style = None
                for i in variant_classifications:
                    if i["number"] == variant[field]:
                        style = i
                if style:
                    if "name" in style:
                        value += style["name"]
                        if "description" in style:
                            value += (
                                f" (" + style["description"].strip().replace("\n","<br>") + ")"
                            )
                    if "color" in style:
                        value_color = style["color"]
            message_variant_classification += f"<tr><td>{field}</td><td width='20'></td><td style='color:{value_color}'>{value}</td></tr>"
    message_variant_classification += "</table>"
    message_variant_counts_freqs += f"{message_variant_counts}{message_variant_freqs}</table>"

    # final message
    message += f"""<hr>{message_variant_classification}"""
    if message_variant_current_infos:
        message += f"""<hr>{message_variant_current_infos}"""
    message += f"""<hr>{message_variant_counts_freqs}"""

    return message
