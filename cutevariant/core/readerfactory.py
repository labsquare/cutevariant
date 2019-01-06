from .reader import *
import os


class ReaderFactory(object):
    """
	Create reader depending file type 
	"""

    def __init__(self):
        pass

    @staticmethod
    def create_reader(filename):

        if not os.path.isfile(filename):
            raise FileExistsError()

        extension = os.path.splitext(filename)[1]

        if extension == ".csv":
            print("create csv reader")
            return CsvReader(open(filename, "r"))

        if extension == ".vcf":
            print("create vcf reader")
            return VcfReader(open(filename, "r"))

        return None
