"""A place to store style rules for the GUI"""
from cutevariant.commons import DIR_STYLES
from PySide6.QtGui import QPalette, QColor


CLASSIFICATION = {
    0: {"name": "Unclassified", "icon": 0xF03A1, "color": "lightgray"},
    1: {"name": "Benin", "icon": 0xF03A4, "color": "#71e096"},
    2: {"name": "Likely benin", "icon": 0xF03A7, "color": "#71e096"},
    3: {
        "name": "Variant of uncertain significance",
        "icon": 0xF03AA,
        "color": "#f5a26f",
    },
    4: {"name": "Likely pathogenic", "icon": 0xF03AD, "color": "#ed6d79"},
    5: {"name": "Pathogenic", "icon": 0xF03B1, "color": "#ed6d79"},
}


GENOTYPE = {
    -1: {"name": "Unknown genotype", "icon": 0xF10D3},
    0: {"name": "Homozygous wild", "icon": 0xF0766},
    1: {"name": "Heterozygous", "icon": 0xF0AA1},
    2: {"name": "Homozygous muted", "icon": 0xF0AA5},
}


FIELD_TYPE = {
    "float": {"name": "floating ", "icon": 0xF0B0D, "color": "#FE604E"},
    "int": {"name": "integer", "icon": 0xF0B10, "color": "#FDA401"},
    "str": {"name": "text", "icon": 0xF0B1A, "color": "#31B1E2"},
    "bool": {"name": "boolean", "icon": 0xF0B09, "color": "#FF618F"},
}

FIELD_CATEGORY = {
    "variants": {"icon": 0xF0B1D},
    "annotations": {"icon": 0xF0B08},
    "samples": {"icon": 0xF0B1A},
}


GENE_COLOR = "#F5A26F"
WARNING_BACKGROUND_COLOR = "#FFCCBA"
WARNING_TEXT_COLOR = "#D73705"

DARK_COLOR = {
    "darkpurple": "#40375C",
    "purple": "#5A4F7C",
    "red": "#F14235",
    "yellow": "#F5A623",
    "green": "#7BBB44",
}


# Sequence ontology colors
SO_COLOR = {
    "stop": "#808080",
    "utr": "#911EB4",
    "splice": "#F58231",
    "intron": "#0082C8",
    "intergenic": "#3CB44B",
    "frameshift": "#E6194B",
    "missense": "#F032E6",
}


class ColorPalette:
    PRIMARY = "red"
    SECONDARY = "red"
    SUCCESS = "red"
    DANGER = "red"
    WARNING = "red"
    INFO = "red"
    LIGHT = "red"
    DARK = "red"

    RED = "red"
    ORANGE = "orange"
    YELLOW = "yellow"
    GREEN = "green"
    BLUE = "blue"
    PURPLE = "purple"


def bright(app):
    """Mock function to don't apply any style to the Qt application instance.

    TODO: Find a way to reset properly and dynamically the effects of `dark()`
    and put it here.

    .. note:: Called my __main__ on startup and not by StyleSettingsWidget for
    the moment (see TODO).
    """

    ColorPalette.PRIMARY_COLOR = "#6200EE"
    ColorPalette.SECONDARY_COLOR = "#3700B3"
    ColorPalette.SUCCESS_COLOR = "#03DAC6"
    ColorPalette.DANGER_COLOR = "red"
    ColorPalette.WARNING_COLOR = "red"
    ColorPalette.INFO_COLOR = "red"
    ColorPalette.LIGHT_COLOR = "red"
    ColorPalette.DARK_COLOR = "red"

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
    lightPalette.setColor(
        QPalette.Disabled, QPalette.HighlightedText, QColor("#FFA2A4A5")
    )

    app.setPalette(lightPalette)

    # _apply_base_theme(app)
    with open(DIR_STYLES + "dark.qss", "r") as file:
        app.setStyleSheet(file.read())


def dark(app):
    """Apply Dark Theme to the Qt application instance.
    Args:
        app (QApplication): QApplication instance.
    """

    ColorPalette.PRIMARY = "#1E9EFF"
    ColorPalette.SECONDARY = "#b4b4b4"
    ColorPalette.TEXT = "#b4b4b4"

    ColorPalette.BASE = "#1F2022"
    ColorPalette.LIGHT = "#2B2F32"
    ColorPalette.DARK = "#1A1B1D"

    ColorPalette.SUCCESS = "#03DAC6"
    ColorPalette.DANGER = "red"
    ColorPalette.WARNING = "red"
    ColorPalette.INFO = "red"

    darkPalette = QPalette()

    # base
    darkPalette.setColor(QPalette.WindowText, QColor(ColorPalette.TEXT))
    darkPalette.setColor(QPalette.Button, QColor(ColorPalette.BASE))
    darkPalette.setColor(QPalette.Light, QColor(ColorPalette.TEXT))
    darkPalette.setColor(QPalette.Midlight, QColor(ColorPalette.LIGHT))
    darkPalette.setColor(QPalette.Dark, QColor(ColorPalette.DARK))
    darkPalette.setColor(QPalette.Text, QColor(ColorPalette.TEXT))
    darkPalette.setColor(QPalette.BrightText, QColor(ColorPalette.LIGHT))
    darkPalette.setColor(QPalette.ButtonText, QColor(ColorPalette.TEXT))

    darkPalette.setColor(QPalette.Base, QColor(ColorPalette.BASE))
    darkPalette.setColor(QPalette.Window, QColor(ColorPalette.BASE))

    darkPalette.setColor(QPalette.Shadow, QColor(ColorPalette.DARK))
    darkPalette.setColor(QPalette.Highlight, QColor(ColorPalette.PRIMARY))
    darkPalette.setColor(QPalette.HighlightedText, QColor(ColorPalette.TEXT))
    darkPalette.setColor(QPalette.Link, QColor(ColorPalette.SECONDARY))
    darkPalette.setColor(QPalette.AlternateBase, QColor(ColorPalette.LIGHT))
    darkPalette.setColor(QPalette.ToolTipBase, QColor(ColorPalette.BASE))
    darkPalette.setColor(QPalette.ToolTipText, QColor(ColorPalette.TEXT))

    darkPalette.setColor(QPalette.PlaceholderText, QColor(127, 127, 127))

    # disabled
    darkPalette.setColor(QPalette.Disabled, QPalette.WindowText, QColor(127, 127, 127))
    darkPalette.setColor(QPalette.Disabled, QPalette.Text, QColor(127, 127, 127))
    darkPalette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(127, 127, 127))
    darkPalette.setColor(QPalette.Disabled, QPalette.Highlight, QColor(80, 80, 80))
    darkPalette.setColor(
        QPalette.Disabled, QPalette.HighlightedText, QColor(127, 127, 127)
    )

    app.setPalette(darkPalette)

    # _apply_base_theme(app)
    with open(DIR_STYLES + "dark.qss", "r") as file:
        app.setStyleSheet(file.read())
