from collections import ChainMap
from cutevariant import LOGGER
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

    def __init__(self, section="app", config_path=None):
        self.section = section
        self.config_path = config_path or QDir(
            QStandardPaths.writableLocation(QStandardPaths.ConfigLocation)
            + QDir.separator()
            + "cutevariant"
        ).absoluteFilePath("config.yml")

        self._user_config = dict()

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
            self._load_from_path(self.default_config_path)
            self.save()

        self._load_from_path(self.config_path)

    def _load_from_path(self, config_path):
        with open(config_path, "r") as stream:
            try:
                self._user_config = yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                LOGGER.critical(exc)
            except KeyError as err:
                print(f"cannot read section {self.section} from config ")

    def save(self):
        if not os.path.exists(os.path.dirname(self.config_path)):
            try:
                os.makedirs(os.path.dirname(self.config_path))
            except OSError as exc:  # Guard against race condition
                if exc.errno != errno.EEXIST:
                    raise

        with open(self.config_path, "w") as stream:
            yaml.dump(self._user_config, stream)

    def reset(self):
        defaut_config = Config(config_path=self.default_config_path)
        self._user_config = defaut_config._user_config

    def __getitem__(self, key: str):
        if self.section in self._user_config:
            return self._user_config[self.section][key]

    def __setitem__(self, key: str, value: typing.Any):
        self.set(key, value)

    def __contains__(self, key):
        return (
            self.section in self._user_config and key in self._user_config[self.section]
        )


if __name__ == "__main__":

    config = Config("global")
    config.load()