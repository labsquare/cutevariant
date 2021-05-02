"""Class for reading, parsing, and downloading data from the Harmonizome API.
"""

import gzip
import json
import os

# Support for both Python2.X and 3.X.
# -----------------------------------------------------------------------------
try:
    from io import StringIO
    from urllib.request import urlopen
    from urllib.error import HTTPError
    from urllib.parse import quote_plus
except ImportError:
    from StringIO import StringIO
    from urllib2 import urlopen, HTTPError
    from urllib import quote_plus

try:
    input_shim = raw_input
except NameError:
    # If `raw_input` throws a `NameError`, the user is using Python 2.X.
    input_shim = input


# Enumerables and constants
# -----------------------------------------------------------------------------


class Enum(set):
    """Simple Enum shim since Python 2.X does not have them."""

    def __getattr__(self, name):
        if name in self:
            return name
        raise AttributeError


# The entity types supported by the Harmonizome API.
class Entity(Enum):

    DATASET = "dataset"
    GENE = "gene"
    GENE_SET = "gene_set"
    ATTRIBUTE = "attribute"
    GENE_FAMILY = "gene_family"
    NAMING_AUTHORITY = "naming_authority"
    PROTEIN = "protein"
    RESOURCE = "resource"


def json_from_url(url):
    """Returns API response after decoding and loading JSON."""
    response = urlopen(url)
    data = response.read().decode("utf-8")
    return json.loads(data)


VERSION = "1.0"
API_URL = "https://maayanlab.cloud/Harmonizome/api"
DOWNLOAD_URL = "https://maayanlab.cloud/static/hdfs/harmonizome/data"

# This config objects pulls the names of the datasets, their directories, and
# the possible downloads from the API. This allows us to add new datasets and
# downloads without breaking this file.
config = json_from_url(API_URL + "/dark/script_config")
DOWNLOADS = [x for x in config.get("downloads")]
DATASET_TO_PATH = config.get("datasets")


# Harmonizome class
# -----------------------------------------------------------------------------


class Harmonizome(object):

    __version__ = VERSION
    DATASETS = DATASET_TO_PATH.keys()

    @classmethod
    def get(cls, entity, name=None, start_at=None):
        """Returns a single entity or a list, depending on if a name is
        provided. If no name is provided and start_at is specified, returns a
        list starting at that cursor position.
        """
        if name:
            name = quote_plus(name)
            return _get_by_name(entity, name)
        if start_at is not None and type(start_at) is int:
            return _get_with_cursor(entity, start_at)
        url = "%s/%s/%s" % (API_URL, VERSION, entity)
        result = json_from_url(url)
        return result

    @classmethod
    def next(cls, response):
        """Returns the next set of entities based on a previous API response."""
        start_at = _get_next(response)
        entity = _get_entity(response)
        return cls.get(entity=entity, start_at=start_at)

    @classmethod
    def download(cls, datasets=None):
        """For each dataset, creates a directory and downloads files into it."""
        # Why not check `if not datasets`? Because in principle, a user could
        # call `download([])`, which should download nothing, not everything.
        # Why might they do this? Imagine that the list of datasets is
        # dynamically generated in another user script.
        if datasets is None:
            datasets = cls.DATASETS
            warning = (
                "Warning: You are going to download all Harmonizome "
                "data. This is roughly 30GB. Do you accept?\n(Y/N) "
            )
            resp = input_shim(warning)
            if resp.lower() != "y":
                return

        for dataset in datasets:
            if dataset not in cls.DATASETS:
                msg = (
                    '"%s" is not a valid dataset name. Check the `DATASETS`'
                    " property for a complete list of names." % dataset
                )
                raise AttributeError(msg)
            if not os.path.exists(dataset):
                os.mkdir(dataset)

            for dl in DOWNLOADS:
                path = DATASET_TO_PATH[dataset]
                url = "%s/%s/%s" % (DOWNLOAD_URL, path, dl)

                try:
                    response = urlopen(url)
                except HTTPError:
                    # Not every dataset has all downloads.
                    pass

                filename = "%s/%s" % (dataset, dl)
                filename = filename.replace(".gz", "")

                if response.code != 200:
                    raise Exception("This should not happen")

                _download_and_decompress_file(response, filename)


# Utility functions
# -------------------------------------------------------------------------


def _get_with_cursor(entity, start_at):
    """Returns a list of entities based on cursor position."""
    url = "%s/%s/%s?cursor=%s" % (API_URL, VERSION, entity, str(start_at))
    result = json_from_url(url)
    return result


def _get_by_name(entity, name):
    """Returns a single entity based on name."""
    url = "%s/%s/%s/%s" % (API_URL, VERSION, entity, name)
    return json_from_url(url)


def _get_entity(response):
    """Returns the entity from an API response."""
    path = response["next"].split("?")[0]
    return path.split("/")[3]


def _get_next(response):
    """Returns the next property from an API response."""
    if response["next"]:
        return int(response["next"].split("=")[1])
    return None


# This function was adopted from here: http://stackoverflow.com/a/15353312.
def _download_and_decompress_file(response, filename):
    """Downloads and decompresses a single file from a response object."""
    compressed_file = StringIO()
    compressed_file.write(response.read())
    compressed_file.seek(0)
    decompressed_file = gzip.GzipFile(fileobj=compressed_file, mode="rb")
    with open(filename, "w+") as outfile:
        outfile.write(decompressed_file.read())


def _download_and_decompress_file(response, filename):
    """"""
    compressed_file = io.BytesIO(response.read())
    decompressed_file = gzip.GzipFile(fileobj=compressed_file)

    with open(filename, "wb+") as outfile:
        outfile.write(decompressed_file.read())
