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
    with open(filepath, "rb") as test_f:
        return binascii.hexlify(test_f.read(2)) == b"1f8b"


def getuncompressedsize(filename):
    with open(filename, "rb") as f:
        f.seek(-4, 2)
        return struct.unpack("I", f.read(4))[0]


def detect_vcf_annotation(filename):
    with open(filename, "r") as file:
        std_reader = vcf.VCFReader(file)
        #print(std_reader.metadata)
        if "VEP" in std_reader.metadata:
            if "CSQ" in std_reader.infos:
                return "vep"

        if "SnpEffVersion" in std_reader.metadata:
            if "ANN" in std_reader.infos:
                return "snpeff"


@contextmanager
def create_reader(filename):

    path = pathlib.Path(filename)

    LOGGER.debug("create_reader: PATH suffix %s, is_gz_file: %s",
                 path.suffixes, is_gz_file(filename))

    if ".vcf" in path.suffixes and ".gz" in path.suffixes:
        annotation_detected = detect_vcf_annotation(filename)
        device = open(filename, "rb")
        reader = VcfReader(device, annotation_detected)
        reader.file_size = getuncompressedsize(filename)
        yield reader
        device.close()
        return

    if ".vcf" in path.suffixes:
        annotation_detected = detect_vcf_annotation(filename)
        device = open(filename, "r")
        reader = VcfReader(device,annotation_detected)
        reader.file_size = os.path.getsize(filename)
        yield reader
        device.close()
        return

    if ".csv" in path.suffixes:
        device = open(filename, "r")
        reader = CsvReader(device)
        reader.file_size = os.path.getsize(filename)
        yield reader
        device.close()
        return


# class ReaderFactory(object):
#     """
# 	Create reader depending file type
# 	"""

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
