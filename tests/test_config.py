import pytest

import tempfile
import os
import yaml

from cutevariant.config import Config


def test_config():
    config_path = tempfile.mktemp()
    config = Config("app", config_path)

    # # Test WRITE
    config["memory"] = 10
    config["network.host"] = "192.168.1.1"

    # Test IN
    assert "memory" in config

    # Test save
    config.save()
    assert os.path.exists(config_path)
    print(config_path)

    with open(config_path) as file:
        data = yaml.safe_load(file)
        assert data["app"]["memory"] == 10
        assert data["app"]["network.host"] == "192.168.1.1"

    # Test READ
    config = Config("app", config_path)

    unknown = config.get("unknown", None)

    assert config["memory"] == 10
    # Test if default config exist
    assert os.path.exists(config.default_config_path)

    # Test reset path
    config.reset()
    assert config["style"] == "bright"
