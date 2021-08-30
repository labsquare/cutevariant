__all__ = ["core", "gui"]
__version__ = "0.3.7"


# Configure logger
from .commons import create_logger

LOGGER = create_logger()
# LOGGER.setLevel("DEBUG")
