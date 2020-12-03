# Custom imports
from cutevariant.gui.formatter import Formatter


class DefaultFormatter(Formatter):

    DISPLAY_NAME = "No style"

    def __init__(self):
        super().__init__()
