__all__ = ["core", "gui"]
__version__ = "0.3.5.dev0"


# Configure logger
from .commons import create_logger

log = create_logger()
log.setLevel("DEBUG")
