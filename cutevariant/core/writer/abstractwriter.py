from cutevariant.core import sql


class AbstractWriter(object):
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
        self.device = device


    def save(self, conn) -> bool:
        raise NotImplemented()






