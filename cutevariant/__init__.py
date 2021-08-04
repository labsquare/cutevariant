__all__ = ["core", "gui"]
__version__ = "0.3.5"


# Configure logger
from .commons import create_logger

LOGGER = create_logger()
# LOGGER.setLevel("DEBUG")
