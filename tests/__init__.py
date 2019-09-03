from cutevariant.commons import logger, LOG_LEVELS

# Enable debug loglevel for tests
LOGGER = logger()
LOGGER.setLevel(LOG_LEVELS["error"])
