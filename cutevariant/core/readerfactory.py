from .reader import *
import os
import struct
from contextlib import contextmanager
import binascii
import pathlib


def is_gz_file(filepath):
    with open(filepath, "rb") as test_f:
        return binascii.hexlify(test_f.read(2)) == b"1f8b"


def getuncompressedsize(filename):
    with open(filename, "rb") as f:
        f.seek(-4, 2)
        return struct.unpack("I", f.read(4))[0]


@contextmanager
def create_reader(filename):

    path = pathlib.Path(filename)

    print("PATH suffix", path.suffixes, is_gz_file(filename))

    if ".vcf" in path.suffixes and ".gz" in path.suffixes:
        device = open(filename, "rb")
        reader = VcfReader(device)
        reader.file_size = getuncompressedsize(filename)
        yield reader
        device.close()
        return

    if ".vcf" in path.suffixes:
        device = open(filename, "r")
        reader = VcfReader(device)
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
