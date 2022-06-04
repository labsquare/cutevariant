"""A place to store style rules for the GUI"""
from cutevariant.constants import DIR_STYLES
from PySide6.QtGui import QPalette, QColor
import sqlite3
from cutevariant.config import Config
from cutevariant.core import sql
from cutevariant import constants as cst

CLASSIFICATION = {
    -1: {
        "name": "Rejected",
        "icon": 0xF00C3,
        "icon_favorite": 0xF00C1,
        "color": "dimgray",
        "blurred": 1,
    },
    0: {
        "name": "Unclassified",
        "icon": 0xF00C3,
        "icon_favorite": 0xF00C1,
        "color": "lightgray",
        "blurred": 0,
    },
    1: {
        "name": "Benin",
        "icon": 0xF00C3,
        "icon_favorite": 0xF00C1,
        "color": "#71e096",
        "blurred": 0,
    },
    2: {
        "name": "Likely benin",
        "icon": 0xF00C3,
        "icon_favorite": 0xF00C1,
        "color": "#71e096",
        "blurred": 0,
    },
    3: {
        "name": "Variant of uncertain significance",
        "icon": 0xF00C3,
        "icon_favorite": 0xF00C1,
        "color": "#f5a26f",
        "blurred": 0,
    },
    4: {"name": "Likely pathogenic", "icon": 0xF00C3, "icon_favorite": 0xF00C1, "color": "#ed6d79"},
    5: {
        "name": "Pathogenic",
        "icon": 0xF00C3,
        "icon_favorite": 0xF00C1,
        "color": "#ed6d79",
        "blurred": 0,
    },
}

SAMPLE_CLASSIFICATION = {
    -1: {"name": "Rejected", "icon": 0xF012F, "color": "dimgray", "blurred": 1, "lock": 1},
    0: {"name": "pending", "icon": 0xF012F, "color": "lightgray", "blurred": 0, "lock": 0},
    1: {"name": "valid", "icon": 0xF012F, "color": "lightgray", "blurred": 0, "lock": 1},
}

SAMPLE_VARIANT_CLASSIFICATION = {
    -1: {"name": "Rejected", "icon": 0xF00C1, "color": "dimgray", "blurred": 1},
    0: {"name": "Unclassified", "icon": 0xF00C1, "color": "lightgray", "blurred": 0},
    1: {"name": "Verification required", "icon": 0xF00C1, "color": "#f5a26f", "blurred": 0},
    2: {"name": "Validated", "icon": 0xF00C1, "color": "#71e096", "blurred": 0},
}

GENOTYPE = {
    -1: {"name": "Unknown genotype", "icon": 0xF10D3},
    0: {"name": "Homozygous wild", "icon": 0xF0766},
    1: {"name": "Heterozygous", "icon": 0xF0AA1},
    2: {"name": "Homozygous muted", "icon": 0xF0AA5},
}


FIELD_TYPE = {
    "float": {"name": "floating ", "icon": 0xF0B0D, "color": "#2e9599"},
    "int": {"name": "integer", "icon": 0xF0B10, "color": "#f7dc68"},
    "str": {"name": "text", "icon": 0xF0B1A, "color": "#f46c3f"},
    "bool": {"name": "boolean", "icon": 0xF0B09, "color": "#a7226f"},
}

FIELD_CATEGORY = {
    "variants": {"icon": 0xF0B1D},
    "annotations": {"icon": 0xF0B08},
    "samples": {"icon": 0xF0B1A},
}


GENE_COLOR = "#F5A26F"
WARNING_BACKGROUND_COLOR = "#FFCCBA"
WARNING_TEXT_COLOR = "#D73705"
BLURRED_COLOR = "dimgray"

DARK_COLOR = {
    "darkpurple": "#40375C",
    "purple": "#5A4F7C",
    "red": "#F14235",
    "yellow": "#F5A623",
    "green": "#7BBB44",
}


def bright(app):
    """Mock function to don't apply any style to the Qt application instance.

    TODO: Find a way to reset properly and dynamically the effects of `dark()`
    and put it here.

    .. note:: Called my __main__ on startup and not by StyleSettingsWidget for
    the moment (see TODO).
    """
    lightPalette = QPalette()
    # base
    lightPalette.setColor(QPalette.WindowText, QColor("#FF1E1E1E"))
    lightPalette.setColor(QPalette.Button, QColor("#E9EBEF"))
    lightPalette.setColor(QPalette.Light, QColor("#FFF5F5F5"))
    lightPalette.setColor(QPalette.Midlight, QColor("#FFCCCEDB"))
    lightPalette.setColor(QPalette.Dark, QColor("#FFA2A4A5"))

    lightPalette.setColor(QPalette.Text, QColor("#434343"))
    lightPalette.setColor(QPalette.BrightText, QColor("#55000000"))
    lightPalette.setColor(QPalette.ButtonText, QColor("#434343"))

    lightPalette.setColor(QPalette.Base, QColor("#F7F9F9"))
    lightPalette.setColor(QPalette.Window, QColor("#E9EBEF"))

    # lightPalette.setColor(QPalette.Shadow, QColor("green"))
    lightPalette.setColor(QPalette.Highlight, QColor("#FF007ACC"))
    lightPalette.setColor(QPalette.HighlightedText, QColor("#FFF5F5F5"))

    lightPalette.setColor(QPalette.Link, QColor("#FF007ACC"))
    lightPalette.setColor(QPalette.AlternateBase, QColor("#F0F1F5"))
    lightPalette.setColor(QPalette.PlaceholderText, QColor("#FFA2A4A5"))

    lightPalette.setColor(QPalette.ToolTipBase, QColor("#FFFDF4BF"))
    lightPalette.setColor(QPalette.ToolTipText, QColor("#FF252526"))

    # disabled
    lightPalette.setColor(QPalette.Disabled, QPalette.WindowText, QColor("#FFA2A4A5"))
    lightPalette.setColor(QPalette.Disabled, QPalette.Text, QColor("#FFA2A4A5"))
    lightPalette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor("#FFA2A4A5"))
    lightPalette.setColor(QPalette.Disabled, QPalette.Highlight, QColor("pink"))
    lightPalette.setColor(QPalette.Disabled, QPalette.HighlightedText, QColor("#FFA2A4A5"))

    app.setPalette(lightPalette)

    # _apply_base_theme(app)
    with open(DIR_STYLES + "dark.qss", "r") as file:
        app.setStyleSheet(file.read())


def dark(app):
    """Apply Dark Theme to the Qt application instance.
    Args:
        app (QApplication): QApplication instance.
    """

    darkPalette = QPalette()

    # base
    darkPalette.setColor(QPalette.WindowText, QColor(180, 180, 180))
    darkPalette.setColor(QPalette.Button, QColor(53, 53, 53))
    darkPalette.setColor(QPalette.Light, QColor(180, 180, 180))
    darkPalette.setColor(QPalette.Midlight, QColor(90, 90, 90))
    darkPalette.setColor(QPalette.Dark, QColor(35, 35, 35))
    darkPalette.setColor(QPalette.Text, QColor(180, 180, 180))
    darkPalette.setColor(QPalette.BrightText, QColor(200, 200, 200))
    darkPalette.setColor(QPalette.ButtonText, QColor(180, 180, 180))

    darkPalette.setColor(QPalette.Base, QColor(42, 42, 42))
    darkPalette.setColor(QPalette.Window, QColor(53, 53, 53))

    darkPalette.setColor(QPalette.Shadow, QColor(20, 20, 20))
    darkPalette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    darkPalette.setColor(QPalette.HighlightedText, QColor(180, 180, 180))
    darkPalette.setColor(QPalette.Link, QColor(56, 252, 196))
    darkPalette.setColor(QPalette.AlternateBase, QColor(66, 66, 66))
    darkPalette.setColor(QPalette.ToolTipBase, QColor(53, 53, 53))
    darkPalette.setColor(QPalette.ToolTipText, QColor(180, 180, 180))

    darkPalette.setColor(QPalette.PlaceholderText, QColor(127, 127, 127))

    # disabled
    darkPalette.setColor(QPalette.Disabled, QPalette.WindowText, QColor(127, 127, 127))
    darkPalette.setColor(QPalette.Disabled, QPalette.Text, QColor(127, 127, 127))
    darkPalette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(127, 127, 127))
    darkPalette.setColor(QPalette.Disabled, QPalette.Highlight, QColor(80, 80, 80))
    darkPalette.setColor(QPalette.Disabled, QPalette.HighlightedText, QColor(127, 127, 127))

    app.setPalette(darkPalette)

    # _apply_base_theme(app)
    with open(DIR_STYLES + "dark.qss", "r") as file:
        app.setStyleSheet(file.read())


# def apply_frameless_style(widget):
#     """Apply frameless style to the given widget

#     TODO: What this style is supposed to do ?
#     """
#     with open(DIR_STYLES + "frameless.qss", "r") as file:
#         widget.setStyleSheet(file.read())


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
    variant_name_pattern = config.get("variant_name_pattern") or "{chr}:{pos} - {ref}>{alt}"

    # all genotype values
    genotype_values_text=""
    for f in genotype:
        v=genotype[f]
        if f not in ["sample_id", "variant_id", "name", "gt", "classification", "tags", "comment"]:
            #f_upper=f.upper()
            f_upper=f
            genotype_values_text+=f"<tr><td>{f_upper}</td><td width='20'></td><td>{v}</td></tr>"
    genotype["genotype_values_text"]=genotype_values_text

    # classification
    config = Config("classifications")
    classifications=config.get("genotypes", [])
    classification=genotype.get("classification", 0)
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
            classification_color=style["color"]
    genotype["classification_text"]=classification_text
    genotype["classification_color"]=classification_color

    # extract info from variant
    variant = sql.get_variant(conn, variant_id, with_annotations=True)
    if len(variant["annotations"]):
        for ann in variant["annotations"][0]:
            variant["annotations___" + str(ann)] = variant["annotations"][0][ann]
    variant_name_pattern = variant_name_pattern.replace("ann.", "annotations___")
    variant_name = variant_name_pattern.format(**variant)
    genotype["variant_name"]=variant_name

    # tag genotype
    if genotype["gt"]:
        genotype_text=GENOTYPE.get(genotype["gt"], "Unknown")["name"]
    else:
        genotype_text="<i>no tag</i>"
    genotype["genotype_text"]=genotype_text

    # tags text
    if genotype["tags"]:
        tags_text=genotype["tags"].replace(","," ")
    else:
        tags_text="<i>no tag</i>"
    genotype["tags_text"]=tags_text

    # comment text
    if genotype["comment"]:
        comment_text=genotype["comment"].replace("\n","<br>")
    else:
        comment_text="<i>no comment</i>"
    genotype["comment_text"]=comment_text

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
    sample_classifications=config.get("samples", [])

    # genotype classification
    config = Config("classifications")
    genotype_classifications=config.get("genotypes", [])
    sample_id=sample["id"]
    sample_nb_genotype_by_classification=sql.get_sample_nb_genotype_by_classification(conn, sample_id)
    nb_validated_genotype=0
    nb_validation_genotype_message=""
    for classification in sample_nb_genotype_by_classification:
        nb_validation_genotype_text=""
        nb_validation_genotype_color=""
        nb_genotype_by_classification=sample_nb_genotype_by_classification[classification]
        if classification>0:
            nb_validated_genotype+=nb_genotype_by_classification
        style = None
        for i in genotype_classifications:
            if i["number"] == classification:
                style = i
        if style:
            if "name" in style:
                nb_validation_genotype_text += style["name"]
                if "description" in style:
                    nb_validation_genotype_text += f" (" + style["description"].strip() + ")"
            if "color" in style:
                nb_validation_genotype_color=style["color"]
        nb_validation_genotype_message+=f"<tr><td style='color:{nb_validation_genotype_color}' align='right'>{nb_genotype_by_classification}</td><td width='10'></td><td>{nb_validation_genotype_text}</td></tr>"
    if nb_validation_genotype_message:
        nb_validation_genotype_message=f"""
            <hr>
            Genotypes classification
            <table>
                {nb_validation_genotype_message}
            </table>
        """

    info_all_fields=""
    info_classification=""
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
                sample_field_value = cst.SEX_DESC.get(int(sample[sample_field]), "Unknown")
            info_all_fields += f"<tr><td>{sample_field}</td><td width='20'></td><td style='color:{sample_field_value_color}'>{sample_field_value}</td></tr>"
        # classification fields
        if sample_field in ["classification", "tags", "comment"]:
            if sample_field == "tags":
                if sample_field_value:
                    sample_field_value = sample_field_value.replace(","," ")
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
                                sample_field_value += f" (" + style["description"].strip() + ")"
                        if "color" in style:
                            sample_field_value_color=style["color"]
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