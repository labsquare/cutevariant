from .reader import *
import os
import struct
from contextlib import contextmanager


@contextmanager
def create_reader(filename):
    extension = os.path.splitext(filename)[1]
    
    if extension == ".vcf":
        device = open(filename,"r")
        yield VcfReader(device)
        device.close()




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




    # def getuncompressedsize(filename): 
    #     with open(filename, 'rb') as f: 
    #         f.seek(-4, 2) 
    #         return struct.unpack('I', f.read(4))[0] 
