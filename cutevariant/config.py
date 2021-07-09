from collections import ChainMap
import os
import yaml
import typing
from PySide2.QtCore import QStandardPaths, QDir, QFile, QFileInfo


class Config:

    """Config class help you to read and write config variables

    Attributes:
        config_path (str): a path to a config file using yaml format
        default_config_path(str, readonly): path to the default config path
        section (str): the key section to use.

    Examples:
        config = Config("app")
        config["memory"] = 10
        # Save into the default location ~/.config/cutevariant/config.yaml
        config.save()

        config = Config("plugin_name")
        max_row = config["max_row"]

        # Reset default config
        config.reset()

    """

    def __init__(self, section="app", config_path=None, load=True):
        self.section = section
        self.config_path = config_path or QDir(
            QStandardPaths.writableLocation(QStandardPaths.ConfigLocation)
            + QDir.separator()
            + "cutevariant"
        ).absoluteFilePath("config.yml")

        self._user_config = dict()

        if load:
            self.load()

    @property
    def default_config_path(self):
        return os.path.dirname(__file__) + os.path.sep + "default_config.yml"

    def get(self, key: str, default=None):

        if self.section not in self._user_config:
            self._user_config[self.section] = {}

        return self._user_config[self.section].get(key, default)

    def set(self, key: str, value: typing.Any):

        if self.section not in self._user_config:
            self._user_config[self.section] = {}

        self._user_config[self.section][key] = value

    def load(self):

        if not os.path.exists(self.config_path):
            self.save()

        with open(self.config_path, "r") as stream:
            try:
                self._user_config = yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                print(exc)
            except KeyError as err:
                print(f"cannot read section {self.section} from config ")

    def save(self):
        with open(self.config_path, "w") as stream:
            yaml.dump(self._user_config, stream)

    def reset(self):
        previous_path = self.config_path
        self.config_path = self.default_config_path
        self.load()
        self.config_path = previous_path
        self.save()

    def __getitem__(self, key: str):
        return self._user_config[self.section][key]

    def __setitem__(self, key: str, value: typing.Any):
        self.set(key, value)

    def __contains__(self, key):
        return key in self._user_config[self.section]


if __name__ == "__main__":

    config = Config("global")
    config.load()

    print(config["style"])
