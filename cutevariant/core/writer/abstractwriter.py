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

    def __init__(self, device, fields_to_export=None):
        self.device = device

        if fields_to_export is None:
            fields_to_export = ["chr", "pos", "ref", "alt"]

        # assert {"chr","pos","ref","alt"}.issubset(fields_to_export), "Fields to export should have at least CHR, POS, REF and ALT"
        self.fields = fields_to_export
        self.filters = dict()
        self.source = "variants"
        self.group_by = []
        self.having = {}
        self.order_by = None
        self.order_desc = False
        self.formatter = None
        self.debug_sql = None

    def async_save(self, conn, *args, **kwargs):
        """
        Yields percentage of progress upon saving fields into device (See :meth: save)
        """
        raise NotImplementedError()

    def save(self, conn, *args, **kwargs) -> bool:
        """
        Write the selected fields for this writer inside device (See :meth: __init__).
        Returns True on success, False otherwise.
        """
        for progress, variant_count in self.async_save(conn, *args, **kwargs):
            LOGGER.debug("Saving %i out of %i", progress + 1, variant_count)
