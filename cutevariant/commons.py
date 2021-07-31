# Standard imports
from logging.handlers import RotatingFileHandler
import logging
import datetime as dt
import re
import json
import tempfile
import os
from pkg_resources import resource_filename

from .bgzf import BgzfBlocks

# Misc
MAX_RECENT_PROJECTS = 5
MIN_COMPLETION_LETTERS = 1
DEFAULT_SELECTION_NAME = "variants"
# version from which database files are supported (included)
MIN_AUTHORIZED_DB_VERSION = "0.2.0"


# ACMG Classification
CLASSIFICATION = {
    0: "Unclassified",
    1: "Benin",
    2: "Likely benin",
    3: "Variant of uncertain significance",
    4: "Likely pathogen",
    5: "Pathogen",
}

CLASSIFICATION_ICONS = {
    0: 0xF03A1,
    1: 0xF03A4,
    2: 0xF03A7,
    3: 0xF03AA,
    4: 0xF03AD,
    5: 0xF03B1,
}

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

# Genotypes
GENOTYPE_ICONS = {-1: 0xF10D3, 0: 0xF0766, 1: 0xF0AA1, 2: 0xF0AA5}

GENOTYPE_DESC = {
    -1: "Unknown genotype",
    0: "Homozygous wild",
    1: "Heterozygous",
    2: "Homozygous muted",
}

# Paths
DIR_LOGS = tempfile.gettempdir() + "/"

DIR_ASSETS = resource_filename(__name__, "assets/")  # current package name
DIR_TRANSLATIONS = DIR_ASSETS + "i18n/"
DIR_FONTS = DIR_ASSETS + "fonts/"
DIR_ICONS = DIR_ASSETS + "icons/"
DIR_STYLES = DIR_ASSETS + "styles/"

BASIC_STYLE = "Bright"
FONT_FILE = DIR_FONTS + "materialdesignicons-webfont.ttf"


REPORT_BUG_URL = "https://github.com/labsquare/cutevariant/issues/new"
WIKI_URL = "https://github.com/labsquare/cutevariant/wiki"

# Logging
log_NAME = "cutevariant"
LOG_LEVEL = "INFO"
LOG_LEVELS = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "notset": logging.NOTSET,
}

################################################################################
def create_logger():
    logger = logging.getLogger(__name__)
    formatter = logging.Formatter(
        "%(levelname)s:[%(dirname)s/%(filename)s:%(lineno)s:%(funcName)s()] %(message)s"
    )

    stdout_handler = logging.StreamHandler()
    stdout_handler.setFormatter(formatter)

    file_handler = logging.FileHandler("cutevariant.log", mode="w")
    file_handler.setFormatter(formatter)

    class MyCustomLogFilter(logging.Filter):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)

        def filter(self, record):
            dirname = os.path.basename(os.path.dirname(record.pathname))
            record.dirname = dirname
            return True

    stdout_handler.addFilter(MyCustomLogFilter())

    logger.addHandler(stdout_handler)
    logger.addHandler(file_handler)

    return logger


def is_gz_file(filepath):
    """Return a boolean according to the compression state of the file"""
    with open(filepath, "rb") as test_f:
        return test_f.read(3) == b"\x1f\x8b\x08"


def get_uncompressed_size(filepath):
    device = open(filepath, "rb")
    magic_4bytes = device.read()[:4]
    #  IT IS A GZIP FILE
    if magic_4bytes == b"\x1f\x8b\x08\x08":
        device.seek(-4, 2)
        return int.from_bytes(device.read(4), byteorder="little")

    #  IT IS A BGZIP FILE
    elif magic_4bytes == b"\x1f\x8b\x08\x04":
        device.seek(0)
        return sum([i[3] for i in BgzfBlocks(device)])

    else:
        device = open(filepath, "rb")
        device.seek(0, os.SEEK_END)
        return device.tell()


def bytes_to_readable(size) -> str:
    """return human readable size from bytes

    Args:
        size (int): size in bytes

    Returns:
        str: readable size
    """
    out = ""
    for count in ["Bytes", "KB", "MB", "GB"]:
        if size > -1024.0 and size < 1024.0:
            return "%3.1f%s" % (size, count)
        size /= 1024.0
    return "%3.1f%s" % (size, "TB")


def snake_to_camel(name: str) -> str:
    """Convert snake_case name to CamelCase name

    Args:
        name (str): a snake string like : query_view

    Returns:
        str: a camel string like: QueryView
    """
    return "".join([i.capitalize() for i in name.split("_")])


def camel_to_snake(name: str) -> str:
    """Convert CamelCase to snake_case name

    Args:
        name (str): a snake string like : QueryView

    Returns:
        str: a camel string like: query_view
    """
    name = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", name).lower()


def is_json_file(filename):

    if not os.path.exists(filename):
        return False

    with open(filename) as file:
        try:
            json.load(file)
        except Exception as e:
            return False

    return True
