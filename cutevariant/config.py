from collections import ChainMap
import os
import yaml
from PySide2.QtCore import QStandardPaths, QDir, QFile, QFileInfo


class Config:
    def __init__(self, root="global", user_config_path=None):

        self.user_config_path = user_config_path or QDir(
            QStandardPaths.writableLocation(QStandardPaths.ConfigLocation)
            + QDir.separator()
            + "cutevariant"
        ).absoluteFilePath("config.yml")

        self.plugins_path = (
            os.path.dirname(__file__)
            + QDir.separator()
            + "gui"
            + QDir.separator()
            + "plugins"
        )

        # Either 'global' or the name of a plugin
        self.root = root

        self.default_config = {}
        self.user_config = {}

        self.load()

    @property
    def root(self):
        """return config root"""
        return self._root

    @root.setter
    def root(self, value: str):
        # TODO : check if value is global or plugins
        self._root = value

    def _create_user_config(self, remove=True):
        """create user config directory"""
        if not os.path.exists(os.path.dirname(self.user_config_path)):
            try:
                os.makedirs(os.path.dirname(self.user_config_path))
            except OSError as exc:  # Guard against race condition
                if exc.errno != errno.EEXIST:
                    raise

        self.reset()
        self.save()

    def load(self):

        # Load default config
        self.default_config = {}

        ## Load global config
        with open(os.path.dirname(__file__) + os.path.sep + "config.yml", "r") as file:
            try:
                self.default_config["global"] = yaml.safe_load(file)
            except yaml.YAMLError as exc:
                print("cannot read default global config")

        ## Load plugins config
        self.default_config["plugins"] = {}
        for plugin in QDir(self.plugins_path).entryInfoList(
            QDir.Dirs | QDir.NoDotDot | QDir.NoDot
        ):
            config_file = QDir(plugin.absoluteFilePath()).absoluteFilePath("config.yml")
            # TODO : test if it is a module
            plugin_name = plugin.baseName()
            if os.path.exists(config_file):
                with open(config_file, "r") as file:
                    try:
                        self.default_config["plugins"][plugin_name] = yaml.safe_load(
                            file
                        )
                    except yaml.YAMLError as exc:
                        print(f"cannot read plugin {plugin_name} config")
            else:
                self.default_config["plugins"][plugin_name] = {}

        # Load user config
        self.user_config = {}

        """ create user config if not exists """
        if not os.path.exists(self.user_config_path):
            self._create_user_config()

        with open(self.user_config_path, "r") as file:
            try:
                self.user_config = yaml.safe_load(file)
            except yaml.YAMLError as exc:
                print("cannot read user config")

    def save(self):
        with open(self.user_config_path, "w") as file:
            yaml.dump(self.user_config, file)

    def reset(self):
        self.user_config = self.default_config

    def __getitem__(self, key):
        """Return user config if exists. Otherwise, returns default settings"""

        # It is a global
        if self.root == "global":
            if self.root in self.user_config:
                return ChainMap(
                    self.user_config[self.root], self.default_config[self.root]
                )[key]

            else:
                return self.default_config[self.root][key]

        # It is a plugins
        elif self.root in self.default_config["plugins"]:
            if self.root in self.user_config.get("plugins", ()):
                return ChainMap(
                    self.user_config["plugins"][self.root],
                    self.default_config["plugins"][self.root],
                )[key]
            else:
                return self.default_plugin_config["plugins"][self.root][key]

    def __setitem__(self, key, value):
        """Set user config"""

        # check if root is a valid root by comparing with default config
        if self.root not in ["global"] + list(self.default_config["plugins"].keys()):
            return

        if self.root not in self.user_config:
            self.user_config[self.root] = {}

        if self.root == "global":
            self.user_config[self.root][key] = value
        else:
            self.user_config[self.root]["plugins"][key] = value


if __name__ == "__main__":

    config = Config("global")
    config["style"] = "blue"
    print(config["style"])

    config.root = "variant_view"
    config["memory_cache"] = 100
    print("dd", config["memory_cache"])

    config.save()
