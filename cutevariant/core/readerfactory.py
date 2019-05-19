# Standard imports
import os
import struct
from contextlib import contextmanager
import binascii
import pathlib

# Custom imports
from .reader import *
import cutevariant.commons as cm
import vcf

LOGGER = cm.logger()


def is_gz_file(filepath):
    """Return a boolean according to the compression state of the file"""
    with open(filepath, "rb") as test_f:
        return binascii.hexlify(test_f.read(2)) == b"1f8b"


def get_uncompressed_size(filename):
    """Get the size of the given compressed file
    This size is stored in the last 4 bytes of the file.
    """
    with open(filename, "rb") as f:
        f.seek(-4, 2)
        return struct.unpack("I", f.read(4))[0]


def detect_vcf_annotation(filename):
    """Return the name of the annotation parser to be used on the given file
    Called: In the importer and in the project wizard to display the detected
    annotations.

    :return: "vep", "snpeff", None
    """
    with open(filename, "r") as file:
        std_reader = vcf.VCFReader(file)
        # print(std_reader.metadata)
        if "VEP" in std_reader.metadata:
            if "CSQ" in std_reader.infos:
                return "vep"

        if "SnpEffVersion" in std_reader.metadata:
            if "ANN" in std_reader.infos:
                return "snpeff"


@contextmanager
def create_reader(filename):
    """Context manager that wraps the given file and return an accurate reader

    A detection of the file type is made as well as a detection of the
    annotations format if required.

    Filetypes and annotations parsers supported:

        - vcf.gz: snpeff, vep
        - vcf: snpeff, vep
        - csv, tsv, txt: vep
    """

    path = pathlib.Path(filename)

    LOGGER.debug(
        "create_reader: PATH suffix %s, is_gz_file: %s",
        path.suffixes,
        is_gz_file(filename),
    )

    if ".vcf" in path.suffixes and ".gz" in path.suffixes:
        # TODO: use is_gz_file() ?
        annotation_detected = detect_vcf_annotation(filename)
        device = open(filename, "rb")
        reader = VcfReader(device, annotation_detected)
        reader.file_size = get_uncompressed_size(filename)
        yield reader
        device.close()
        return

    if ".vcf" in path.suffixes:
        annotation_detected = detect_vcf_annotation(filename)
        device = open(filename, "r")
        reader = VcfReader(device, annotation_detected)
        reader.file_size = os.path.getsize(filename)
        yield reader
        device.close()
        return

    if {".tsv", ".csv", ".txt"} & set(path.suffixes):
        device = open(filename, "r")
        reader = CsvReader(device)
        reader.file_size = os.path.getsize(filename)
        yield reader
        device.close()
        return

    raise Exception("create_reader:: Could not choose parser for this file.")


# class ReaderFactory(object):
#     """
#   Create reader depending file type
#   """

#     def __init__(self):
#         pass

#     @staticmethod
#     def create_reader(filename):

#         if not os.path.isfile(filename):
#             raise FileExistsError()

#         extension = os.path.splitext(filename)[1]

#         if extension == ".csv":
#             print("create csv reader")
#             return CsvReader(open(filename, "r"))

#         if extension == ".vcf":
#             print("create vcf reader")
#             return VcfReader(open(filename, "r"))

#         if extension == ".vcf":
#             print("create vcf reader")
#             return VcfReader(open(filename, "r"))

#         return None
