import pytest

import tempfile
import os
import yaml

from cutevariant.config import Config


@pytest.fixture
def config():
    c = Config(user_config_path=tempfile.mktemp())
    assert "global" in c.default_config
    return c


def test_config(config: Config):
    assert os.path.exists(config.user_config_path)

    config.default_config["global"]["test"] = "sacha"
    assert config["test"] == "sacha"

    config["test2"] = "charles"
    assert config["test2"] == "charles"

    config.save()

    with open(config.user_config_path, "r") as f:
        config_data = yaml.safe_load(f)
        assert config_data["global"]["test2"] == "charles"
