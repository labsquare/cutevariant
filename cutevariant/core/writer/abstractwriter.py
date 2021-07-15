# Custom imports
from cutevariant.core import command as cmd
from cutevariant.core.querybuilder import build_sql_query
import cutevariant.commons as cm

from cutevariant import LOGGER


class AbstractWriter:
    """Base class for all Writer required to export variants into a file or a database.

    Subclass it if you want a new file writer.

    Attributes:

        device: a file object typically returned by open("w")

    Example:

        with open(filename,"rw") as file:
            writer = MyWriter(file)
            writer.save(conn)
    """

    def __init__(
        self,
        conn,
        device,
        fields=["chr", "pos", "ref", "alt"],
        source="variants",
        filters={},
    ):

        self.fields = fields
        self.source = source
        self.filters = filters
        self.conn = conn
        self.device = device

    def async_save(self, *args, **kwargs):
        """
        This an asynchronous methods.
        You must yield number of variants saved
        """
        raise NotImplementedError()

    def save(self, *args, **kwargs):

        for count in self.async_save(args, kwargs):
            LOGGER.info(f"{count} variants saved")

    def total_count(self) -> int:
        """
        Returns the total number of fields that will get written.
        You may call anything a field, just make sure that in async_save you're yielding total_count() times at the StopIteration
        """

        return cmd.count_cmd(
            self.conn, fields=self.fields, source=self.source, filters=self.filters
        )["count"]

    def get_variants(self):

        yield from cmd.select_cmd(
            self.conn,
            fields=self.fields,
            source=self.source,
            filters=self.filters,
            limit=None,
        )
