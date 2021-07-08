from collections import ChainMap
import os
import yaml
from PySide2.QtCore import QStandardPaths, QDir, QFile, QFileInfo


class Config:
    def __init__(self, root="global"):

        self.user_config_path = QDir(
            QStandardPaths.writableLocation(QStandardPaths.ConfigLocation)
            + QDir.separator()
            + "cutevariant"
        ).absoluteFilePath("config.yml")

        self.plugins_path = (
            os.getcwd() + QDir.separator() + "gui" + QDir.separator() + "plugins"
        )

        self.root = root
        self._create_user_config()
        self.load()

    @property
    def root(self):
        """ return config root"""
        return self._root

    @root.setter
    def root(self, value: str):
        # TODO : check if value is global or plugins
        self._root = value

    def _create_user_config(self, remove=False):
        """ create user config file """
        if not os.path.exists(os.path.dirname(self.user_config_path)):
            try:
                os.makedirs(os.path.dirname(self.user_config_path))
            except OSError as exc:  # Guard against race condition
                if exc.errno != errno.EEXIST:
                    raise

        if not os.path.exists(self.user_config_path) or remove is True:
            with open(self.user_config_path, "w") as file:
                data = {"global": {"style": "dark"}}
                yaml.dump(data, file)

    def load(self):

        # Load user config
        with open(self.user_config_path, "r") as file:
            try:
                self.user_config = yaml.safe_load(file)
            except yaml.YAMLError as exc:
                print("cannot read user config")

        # Load default config
        ## Load global config
        with open(os.getcwd() + os.path.sep + "config.yml", "r") as file:
            try:
                self.default_global_config = yaml.safe_load(file)
            except yaml.YAMLError as exc:
                print("cannot read default global config")

        ## Load plugins
        self.default_plugin_config = {}
        for plugin in QDir(self.plugins_path).entryInfoList(
            QDir.Dirs | QDir.NoDotDot | QDir.NoDot
        ):
            config_file = QDir(plugin.absoluteFilePath()).absoluteFilePath("config.yml")
            # TODO : test if it is a module
            plugin_name = plugin.baseName()
            if os.path.exists(config_file):
                with open(config_file, "r") as file:
                    try:
                        self.default_plugin_config[plugin_name] = yaml.safe_load(file)
                    except yaml.YAMLError as exc:
                        print(f"cannot read plugin {plugin_name} config")
            else:
                self.default_plugin_config[plugin_name] = {}

            # self.default_plugin_config

    def __getitem__(self, key):
        """ Return user config if exists. Otherwise, returns default settings  """
        if self.root == "global":
            if "global" in self.user_config:
                return ChainMap(self.user_config["global"], self.default_global_config)[
                    key
                ]
            else:
                return self.default_global_config[key]

        # It is a plugins
        elif self.root in self.default_plugin_config:
            if self.root in self.user_config.get("plugins", ()):
                return ChainMap(
                    self.user_config["plugins"][self.root],
                    self.default_plugin_config[self.root],
                )[key]
            else:
                return self.default_plugin_config[self.root][key]
