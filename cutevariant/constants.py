# Misc
import logging
import tempfile

from pkg_resources import resource_filename
from PySide6.QtWidgets import QApplication

# Logging

LOG_LEVEL = "INFO"
LOG_LEVELS = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "notset": logging.NOTSET,
}


MAX_RECENT_PROJECTS = 5
MIN_COMPLETION_LETTERS = 1
DEFAULT_SELECTION_NAME = "variants"
SAMPLES_SELECTION_NAME = "samples"
CURRENT_SAMPLE_SELECTION_NAME = "current_sample"

# version from which database files are supported (included)
MIN_AUTHORIZED_DB_VERSION = "0.2.0"


OPERATORS_PY_2_SQL = {
    "$eq": "=",
    "$gt": ">",
    "$gte": ">=",
    "$lt": "<",
    "$lte": "<=",
    "$in": "IN",
    "$ne": "!=",
    "$nin": "NOT IN",
    "$regex": "REGEXP",
    "$and": "AND",
    "$or": "OR",
}

OPERATORS_SQL_2_PY = {
    "=": "$eq",
    ">": "$gt",
    ">=": "$gte",
    "<": "$lt",
    "<=": "$lte",
    "IN": "$in",
    "!=": "$ne",
    "NOT IN": "$nin",
    "~": "$regexp",
    "AND": "$and",
    "OR": "$or",
}

# OPERATOR HAS
HAS_OPERATOR = ","

# FIELD TYPE
FIELD_TYPE = {
    "float": {"name": "floating ", "icon": 0xF0B0D, "color": "blue"},
    "int": {"name": "integer", "icon": 0xF0B10, "color": "green"},
    "str": {"name": "text", "icon": 0xF0B1A, "color": "purple"},
    "bool": {"name": "boolean", "icon": 0xF0B09, "color": "orange"},
}

# Phenotype
PHENOTYPE_DESC = {2: "Affected", 1: "Unaffected"}

# Genotypes
GENOTYPE_ICONS = {-1: 0xF10D3, 0: 0xF0766, 1: 0xF0AA1, 2: 0xF0AA5}

GENOTYPE_DESC = {
    -1: "Unknown genotype",
    0: "Homozygous wild",
    1: "Heterozygous",
    2: "Homozygous muted",
}

# Sex
SEX_DESC = {1: "Male", 2: "Female"}

# Paths
DIR_LOGS = tempfile.gettempdir() + "/"

SAMPLE_ICON = 0xF0C0B
VARIANT_ICON = 0xF0C2B
GENOTYPE_ICON = 0xF0BFE

DIR_ASSETS = resource_filename(__name__, "assets/")  # current package name
DIR_TRANSLATIONS = DIR_ASSETS + "i18n/"
DIR_FONTS = DIR_ASSETS + "fonts/"
DIR_ICONS = DIR_ASSETS + "icons/"
DIR_STYLES = DIR_ASSETS + "styles/"

BASIC_STYLE = "Bright"
FONT_FILE = DIR_FONTS + "materialdesignicons-webfont.ttf"


REPORT_BUG_URL = "https://github.com/labsquare/cutevariant/issues/new"
WIKI_URL = "https://github.com/labsquare/cutevariant/wiki"
