from cutevariant.core import command as cmd
from cutevariant.core.querybuilder import build_full_sql_query

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
            fields_to_export = ["chr","pos","ref","alt"]
        
        assert {"chr","pos","ref","alt"}.issubset(fields_to_export), "Fields to export should have at least CHR, POS, REF and ALT"
        self.fields = fields_to_export
        self.filters = dict()
        self.source = "variants"
        self.group_by = []
        self.having = {}
        self.order_by = None
        self.order_desc = False
        self.formatter = None
        self.debug_sql = None


    def load_variants(self,conn,offset,limit) -> bool:
        """
        This function loads limit variants from the table, at the given offset.
        You should call it from async_save to load variants chunk by chunk, in order to yield the progress.
        """
        if conn is None:
            return False

        load_args = {
            "fields":self.fields,
            "source":self.source,
            "filters":self.filters,
            "limit":limit,
            "offset":offset,
            "order_desc":self.order_desc,
            "order_by":self.order_by,
            "group_by":self.group_by,
            "having":self.having
        }
        # -------------------------These two guys below **SHOULD** work but don't. Though the last one passes the test so...
        # result = [dict(variant) for variant in cmd.select_cmd(conn,**load_args)]
        # result = [dict(variant) for variant in conn.execute(build_full_sql_query(conn,**load_args))]
        result = [dict(row) for row in conn.execute(f"SELECT {','.join(self.fields)} FROM {self.source} LIMIT {limit} OFFSET {offset}")]
        
        return result

    
    def async_save(self, conn, *args, **kwargs):
        """
        Dump data to a file
        Should write in the file chunk by chunk, yielding the one-based index of the last one written
        """
        raise NotImplementedError()

    def save(self, conn, *args, **kwargs) -> bool:
        for pageno in self.async_save(conn,*args,**kwargs):
            print(f"Wrote page {pageno}")