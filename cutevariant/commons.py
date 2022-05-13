# Standard imports
import logging
import re
import json
import os

from .bgzf import BgzfBlocks

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
