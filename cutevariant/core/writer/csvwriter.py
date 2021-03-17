import csv

from .abstractwriter import AbstractWriter


class CsvWriter(AbstractWriter):
    """Writer allowing to export variants of a project into a CSV file.

    Attributes:

        device: a file object typically returned by open("w")

    Example:
        >>> with open(filename,"rw") as file:
        ...    writer = MyWriter(file)
        ...    writer.save(conn)
    """

    def __init__(self, device, fields_to_export=None):
        super().__init__(device,fields_to_export)

    def async_save(self, conn, *args, **kwargs):
        r"""Iteratively dumps variants into CSV file
        This function creates a generator that yields progress

        Examples::

            chr pos     ref alt
            11  10000   G   T
            11  120000  G   T

        Args:
            **kwargs (dict, optional): Arguments can be given to override
                individual formatting parameters in the current dialect.
            Examples of useful kwargs:
                delimiter : How the fields are separated in the CSV file
                lineterminator : How the lines end in the CSV file
        """
        
        offset = 0
        limit = 50

        # If we know the variant count in advance, let's use it to report relative progress
        if "variant_count" in kwargs:
            variant_count = kwargs["variant_count"]

        dict_writer_args = {"f" : self.device,
                            "delimiter" : "\t",
                            "lineterminator" : "\n",
                            }

        dict_writer_args.update(kwargs)
        
        #Set fieldnames after updating with kwargs to make sure they are not provided by this method's call
        dict_writer_args["fieldnames"] = list(self.fields)

        writer = csv.DictWriter(**dict_writer_args)
        writer.writeheader()

        query_chunk = self.load_variants(conn,0,50) # Get the first records before starting the loop
        while len(query_chunk)>0:
            lines = [{k:v for k,v in variant.items() if k in self.fields} for variant in query_chunk]
            
            writer.writerows(lines)
            # Yield the page number corresponding to the chunk written (one-based index...)
            yield (offset/limit)+1
            offset += limit
            query_chunk = self.load_variants(conn,offset,limit)
        
