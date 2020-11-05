
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

    def __init__(self, device):
        self.device = device

    def save(self, conn, *args, **kwargs) -> bool:
        """Dump data to a file"""
        raise NotImplementedError()
