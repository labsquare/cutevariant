from cutevariant.core import sql
from .abstractwriter import AbstractWriter
import csv 

class CsvWriter(AbstractWriter):
    """Base class for all Writer required to export variants into a file or a database.
    Subclass it if you want a new file writer .

    Attributes:
        device: a file object typically returned by open("w")

    Example:
        with open(filename,"rw") as file:
            writer = MyWriter(file)
            writer.save(conn)
    """

    def __init__(self, device):
        super(AbstractWriter, self).__init__()
        super().__init__(device)
        self.delimiter = "\t"
        self.quotechar="|" 


    def save(self, conn) -> bool:
        
        writer = csv.writer(self.device, delimiter=self.delimiter, quotechar = self.quotechar)
        for row in sql.QueryBuilder(conn).items():
            writer.writerow(row)







