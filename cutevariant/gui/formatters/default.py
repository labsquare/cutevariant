# Custom imports
from cutevariant.gui.formatter import Formatter


class DefaultFormatter(Formatter):

    DISPLAY_NAME = "Basic"

    def __init__(self):
        super().__init__()
