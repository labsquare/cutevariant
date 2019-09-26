from PySide2.QtCore import QSettings
from PySide2.QtNetwork import QNetworkAccessManager, QNetworkProxy

PROXY_TYPES = {
    "No Proxy": QNetworkProxy.NoProxy,
    "Default": QNetworkProxy.DefaultProxy,
    "Sock5": QNetworkProxy.Socks5Proxy,
    "Http": QNetworkProxy.HttpProxy,
}

def get_network_manager():

    # Get proxy settings data
    settings = QSettings("labsquare","cutevariant")
    settings.beginGroup("proxy")
    p_type_index = int(settings.value("type"))
    p_type = list(PROXY_TYPES.values())[p_type_index]
    p_host = settings.value("host")
    p_port = int(settings.value("port"))
    p_username = settings.value("username")
    p_password = settings.value("password")
    settings.endGroup()

    # Create network access manager
    network_manager = QNetworkAccessManager()

    if p_type is not QNetworkProxy.NoProxy:
        proxy = QNetworkProxy(p_type, p_host, p_port,p_username, p_password)
        network_manager.setProxy(proxy)

    return network_manager



