# Standard imports
import logging
import re
import json
import os
import shutil

from .bgzf import BgzfBlocks

from PySide6.QtGui import QColor

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


def create_fake_conn():
    from cutevariant.core.reader import FakeReader
    from cutevariant.core import sql

    conn = sql.get_sql_connection(":memory:")
    sql.import_reader(conn, FakeReader())
    return conn


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


    >>> snake_to_camel("query_view")
    'QueryView'


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


def contrast_color(color: QColor, factor=200):

    luminance = (0.299 * color.red() + 0.587 * color.green() + 0.114 * color.blue()) / 255

    if luminance > 0.5:
        new_color = color.darker(factor)
    else:
        new_color = color.lighter(factor)

    return new_color


def recursive_overwrite(src: str, dest: str, ignore=None):
    """Credits to https://stackoverflow.com/a/15824216
    Recursively copy a file or directory, overwriting files if they exist

    Args:
        src (_type_): source file or directory
        dest (_type_): destination
        ignore (_type_, optional): ignored files
    """
    if os.path.isdir(src):
        if not os.path.isdir(dest):
            os.makedirs(dest)
        files = os.listdir(src)
        if ignore is not None:
            ignored = ignore(src, files)
        else:
            ignored = set()
        for f in files:
            if f not in ignored:
                recursive_overwrite(os.path.join(src, f), os.path.join(dest, f), ignore)
    else:
        shutil.copyfile(src, dest)


def find_variant_name(conn, variant_id: int, troncate=False, troncate_len: int = 40):
    """Find variant name from annotations and a pattern in settings

    Args:
        conn: database connexion
        variant_id (int): variant ID
        troncate (bool, optional): If name need to be troncated
        troncate_len (int, optional): max len of variant name if need to be troncated  
    """
    from cutevariant.config import Config
    from cutevariant.core import sql

    if not conn:
        return "unknown"

    # Get variant_name_pattern
    config = Config("variables") or {}
    variant_name_pattern = config.get("variant_name_pattern") or "{chr}:{pos} - {ref}>{alt}"

    # Get fields
    if variant_id:
        with_annotations = re.findall("ann.", variant_name_pattern)
        variant = sql.get_variant(conn, variant_id, with_annotations=with_annotations)
        if len(variant["annotations"]) and with_annotations:
            for ann in variant["annotations"][0]:
                variant["annotations___" + str(ann)] = variant["annotations"][0][ann]
            variant_name_pattern = variant_name_pattern.replace("ann.", "annotations___")
        variant_name = variant_name_pattern.format(**variant)
    else:
        variant_name = "unknown"

    # Troncate variant name
    if troncate and len(variant_name) > troncate_len:
        troncate_position = int(troncate_len / 2)
        variant_name = variant_name[0:troncate_position] + "..." + variant_name[-troncate_position:]
    
    return variant_name
