from PySide2.QtCore import QSettings
from PySide2.QtNetwork import QNetworkAccessManager, QNetworkProxy

from cutevariant.commons import logger


LOGGER = logger()

PROXY_TYPES = {
    "No Proxy": QNetworkProxy.NoProxy,
    "Default": QNetworkProxy.DefaultProxy,
    "Sock5": QNetworkProxy.Socks5Proxy,
    "Http": QNetworkProxy.HttpProxy,
}


def get_network_manager():

    # Create network access manager
    network_manager = QNetworkAccessManager()

    # Get proxy settings data
    settings = QSettings("labsquare", "cutevariant")
    settings.beginGroup("proxy")
    p_type_index = settings.value("type", 0)
    p_host = settings.value("host")
    p_port = settings.value("port", 80)
    p_username = settings.value("username")
    p_password = settings.value("password")
    settings.endGroup()

    try:
        p_type = list(PROXY_TYPES.values())[int(p_type_index)]

        if p_port:
            p_port = int(p_port)

        if p_type is not QNetworkProxy.NoProxy:
            proxy = QNetworkProxy(p_type, p_host, p_port, p_username, p_password)
            network_manager.setProxy(proxy)
    except Exception as e:
        LOGGER.exception(e)
        pass

    return network_manager
