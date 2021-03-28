# Custom imports
from cutevariant.core import command as cmd
from cutevariant.core.querybuilder import build_full_sql_query
import cutevariant.commons as cm

LOGGER = cm.logger()


class AbstractWriter:
    """Base class for all Writer required to export variants into a file or a database.

    Subclass it if you want a new file writer.

    Attributes:

        device: a file object typically returned by open("w")

    Example:

        >>> with open(filename,"rw") as file:
        ...    writer = MyWriter(file)
        ...    writer.save(conn)
    """

    def __init__(self, conn, device):

        # assert {"chr","pos","ref","alt"}.issubset(fields_to_export), "Fields to export should have at least CHR, POS, REF and ALT"
        self.device = device
        self.conn = conn
        self.fields = ["chr", "pos", "ref", "alt"]
        self.filters = dict()
        self.source = "variants"
        self.group_by = []
        self.having = {}
        self.order_by = None
        self.order_desc = False
        self.formatter = None
        self.debug_sql = None

    def async_save(self, *args, **kwargs):
        """
        Yields a tuple (number_of_variants_saved, total_variants_count) upon saving fields into device (See :meth: save)
        """
        raise NotImplementedError()

    def total_count(self) -> int:
        """
        Returns the total number of fields that will get written.
        You may call anything a field, just make sure that in async_save you're yielding total_count() times at the StopIteration
        """
        raise NotImplementedError()

    def save(self, *args, **kwargs) -> bool:
        """
        Write the selected fields for this writer inside device (See :meth: __init__).
        Returns True on success, False otherwise.
        """
        for progress, variant_count in self.async_save(*args, **kwargs):
            LOGGER.info("Saving %i out of %i", progress + 1, variant_count)
