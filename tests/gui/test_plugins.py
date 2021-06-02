import pytest
from PySide2.QtWidgets import QMainWindow
from cutevariant.gui import plugin
from tests import utils


@pytest.fixture
def conn():
    return utils.create_conn()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self._state = {
            "fields": ["chr", "pos", "ref", "alt"],
            "filters": {},
            "source": "variants",
            "current_variant": {"id": 1},
            "executed_query_data": {"count": 100, "elapsed_time": 3.0},
        }

        self.step_counter = {}

    def on_register(self):
        pass

    def refresh_plugins(self, sender):
        pass

    def on_open_project(self):
        pass

    def set_state_data(self, key, value):
        self._state[key] = value

    def get_state_data(self, key):
        return self._state[key]


def test_find_plugins(qtbot, conn):

    fake_mainwindow = MainWindow()

    for plugin_desc in plugin.find_plugins():

        assert "name" in plugin_desc
        assert "title" in plugin_desc
        assert "description" in plugin_desc
        assert "long_description" in plugin_desc
        assert "version" in plugin_desc

        if "widget" in plugin_desc:

            plugin_widget_class = plugin_desc["widget"]
            assert issubclass(plugin_widget_class, plugin.PluginWidget)

            # check mandatory method
            w = plugin_widget_class()
            #  w.on_register(fake_mainwindow) ===> DOESNT WORK ??
            w.mainwindow = fake_mainwindow

            w.conn = conn

            w.on_refresh()
