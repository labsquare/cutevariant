from PySide2.QtWidgets import QMainWindow

from cutevariant.gui.state import State
from cutevariant.gui import plugin

from tests import utils
import pytest


@pytest.fixture
def conn():
    return utils.create_conn()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.state = State()


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

            # w.on_open_project(conn) ==> DOESNT WORK ??
            w.conn = conn

            w.on_refresh()
