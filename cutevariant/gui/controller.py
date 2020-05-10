
from PySide2.QtCore import QObject
from cutevariant.gui.plugin import PluginWidget

from cutevariant import commons as cm 

LOGGER = cm.logger()


class Controller(object):

    def __init__(self):

        super().__init__()

        self.fields = ["chr", "pos","ref","alt"]
        self.source = "variants"
        self.filters = {}
        self.group_by = []
        self.plugins = {}


    @property
    def conn(self):
        return self._conn
    
    @conn.setter
    def conn(self, value):
        self._conn = value 
        for name, _plugin in self.plugins.items():
            _plugin.on_open_project(self._conn)



    def get_plugin(self, name) -> PluginWidget:
        """ Return plugin by name """ 

        if name in self.plugins:
            return self.plugins[name]

        else:
            return None

    def add_plugin(self, name:str, plugin : PluginWidget):
        self.plugins[name] = plugin

    def refresh_plugins(self, sender = None):
        for plugin in self.plugins.values():
            if plugin != sender:
                LOGGER.info(f"refresh {plugin}")
                plugin.on_refresh()