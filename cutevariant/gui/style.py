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
    darkPalette.setColor(
        QPalette.Disabled, QPalette.HighlightedText, QColor(127, 127, 127)
    )

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
