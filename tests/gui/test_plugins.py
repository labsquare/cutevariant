import pytest
from PySide6.QtWidgets import QMainWindow
from cutevariant.gui import plugin
from tests import utils


@pytest.fixture
def conn():
    return utils.create_conn()


def test_find_plugins(qtbot, conn):

    mainwindow = utils.create_mainwindow()
    mainwindow.conn = conn

    for plugin_desc in plugin.find_plugins():

        assert "name" in plugin_desc
        assert "title" in plugin_desc
        assert "description" in plugin_desc
        assert "long_description" in plugin_desc
        assert "version" in plugin_desc

        if "widget" in plugin_desc:

            Plugin_widget_class = plugin_desc["widget"]
            assert issubclass(Plugin_widget_class, plugin.PluginWidget)

            if Plugin_widget_class.ENABLE:
                instance = Plugin_widget_class()
                qtbot.addWidget(instance)
                instance.mainwindow = mainwindow  # TODO .. .refactor
                instance.on_register(mainwindow)
                print(instance)
                instance.on_refresh()

        #     # check mandatory method
        #     w = plugin_widget_class()
        #     #  w.on_register(fake_mainwindow) ===> DOESNT WORK ??
        #     w.mainwindow = fake_mainwindow
        #     w.mainwindow.conn = conn

        #     w.conn = conn

        #     w.on_refresh()
