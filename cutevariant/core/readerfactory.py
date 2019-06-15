# Standard imports
import os
import struct
from contextlib import contextmanager
import pathlib

# Custom imports
from .reader import *
import cutevariant.commons as cm
import vcf

LOGGER = cm.logger()


def is_gz_file(filepath):
    """Return a boolean according to the compression state of the file"""
    with open(filepath, "rb") as test_f:
        return test_f.read(3) == b"\x1f\x8b\x08"


def get_uncompressed_size(filepath):
    """Get the size of the given compressed file
    This size is stored in the last 4 bytes of the file.
    """
    with open(filepath, "rb") as f:
        f.seek(-4, 2)
        return struct.unpack("I", f.read(4))[0]


def detect_vcf_annotation(filepath):
    """Return the name of the annotation parser to be used on the given file
    Called: In the importer and in the project wizard to display the detected
    annotations.

    :return: "vep", "snpeff", None
    """
    if is_gz_file(filepath):
        # Open .gz files in binary mode (See #84)
        device = open(filepath, "rb")
    else:
        device = open(filepath, "r")

    std_reader = vcf.VCFReader(device)
    # print(std_reader.metadata)
    if "VEP" in std_reader.metadata:
        if "CSQ" in std_reader.infos:
            device.close()
            return "vep"

    if "SnpEffVersion" in std_reader.metadata:
        if "ANN" in std_reader.infos:
            device.close()
            return "snpeff"


@contextmanager
def create_reader(filepath):
    """Context manager that wraps the given file and return an accurate reader

    A detection of the file type is made as well as a detection of the
    annotations format if required.

    Filetypes and annotations parsers supported:

        - vcf.gz: snpeff, vep
        - vcf: snpeff, vep
        - csv, tsv, txt: vep
    """

    path = pathlib.Path(filepath)

    LOGGER.debug(
        "create_reader: PATH suffix %s, is_gz_file: %s",
        path.suffixes,
        is_gz_file(filepath),
    )

    if ".vcf" in path.suffixes and ".gz" in path.suffixes:
        annotation_detected = detect_vcf_annotation(filepath)
        device = open(filepath, "rb")
        reader = VcfReader(device, annotation_detected)
        reader.file_size = get_uncompressed_size(filepath)
        yield reader
        device.close()
        return

    if ".vcf" in path.suffixes:
        annotation_detected = detect_vcf_annotation(filepath)
        device = open(filepath, "r")
        reader = VcfReader(device, annotation_detected)
        reader.file_size = os.path.getsize(filepath)
        yield reader
        device.close()
        return

    if {".tsv", ".csv", ".txt"} & set(path.suffixes):
        device = open(filepath, "r")
        reader = CsvReader(device)
        reader.file_size = os.path.getsize(filepath)
        yield reader
        device.close()
        return

    raise Exception("create_reader:: Could not choose parser for this file.")
