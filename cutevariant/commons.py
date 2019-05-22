# Standard imports
from logging.handlers import RotatingFileHandler
import logging
import datetime as dt
import tempfile
from pkg_resources import resource_filename

# Misc
MAX_RECENT_PROJECTS = 5
MIN_COMPLETION_LETTERS = 1
DEFAULT_SELECTION_NAME = "variants"

# Paths
DIR_LOGS = tempfile.gettempdir() + "/"

DIR_ASSETS = resource_filename(__name__, "assets/")  # current package name
DIR_TRANSLATIONS = DIR_ASSETS + "i18n/"
DIR_FONTS = DIR_ASSETS + "fonts/"
DIR_ICONS = DIR_ASSETS + "icons/"
DIR_STYLES= DIR_ASSETS + "styles/"

GENOTYPE_ICONS = {
    0: 0xf130,
    1: 0xfaa0,
    2: 0Xfaa4,
    -1: 0xf625
}

# Websites and variant query
WEBSITES_URLS = {"varsome": "https://varsome.com/variant/hg19/{chr}-{pos}-{ref}-{alt}"}


# Logging
LOGGER_NAME = "cutevariant"
LOG_LEVEL = "WARNING"
LOG_LEVELS = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "notset": logging.NOTSET,
}

################################################################################


def logger(name=LOGGER_NAME, logfilename=None):
    """Return logger of given name, without initialize it.

    Equivalent of logging.getLogger() call.
    """
    return logging.getLogger(name)


_logger = logging.getLogger(LOGGER_NAME)
_logger.setLevel(LOG_LEVEL)

# log file
formatter = logging.Formatter("%(asctime)s :: %(levelname)s :: %(message)s")
file_handler = RotatingFileHandler(
    DIR_LOGS
    + LOGGER_NAME
    + "_"
    + dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    + ".log",
    "a",
    100_000_000,
    1,
)
file_handler.setLevel(LOG_LEVEL)
file_handler.setFormatter(formatter)
_logger.addHandler(file_handler)

# terminal log
stream_handler = logging.StreamHandler()
formatter = logging.Formatter("%(levelname)s: %(message)s")
stream_handler.setFormatter(formatter)
stream_handler.setLevel(LOG_LEVEL)
_logger.addHandler(stream_handler)


def log_level(level):
    """Set terminal/file log level to given one.
    .. note:: Don't forget the propagation system of messages:
        From logger to handlers. Handlers receive log messages only if
        the main logger doesn't filter them.
    """
    # Main logger
    _logger.setLevel(level.upper())
    # Handlers
    [
        handler.setLevel(level.upper())
        for handler in _logger.handlers
        if handler.__class__
        in (logging.StreamHandler, logging.handlers.RotatingFileHandler)
    ]
