 
from cutevariant.gui import plugin
from PySide2.QtWidgets import *
from PySide2.QtCore import QUrl, QSettings
from PySide2.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from cutevariant.gui.plugins.myvariant.qjsonmodel import QJsonModel
from cutevariant.gui.settings import BaseWidget, GroupWidget
import json
import logging

# TODO => R/W settings more abstract
def read_settings():
    
    settings = QSettings()
    settings.beginGroup("plugins/myvariants.info")
    out = dict()
    for key in settings.allKeys():
        out[key] = settings.value(key)

    if "endpoint" not in out:
        out["endpoint"] = "https://myvariant.info/v1/variant/"

    return out    

def write_settings(data):
    settings = QSettings()
    settings.beginGroup("plugins/myvariants.info")
    for key, value in data.items():
        settings.setValue(key, value)



class SettingsPage(BaseWidget):
    def __init__(self):
        super().__init__()
        self.url_edit = QLineEdit()
        layout = QFormLayout()
        layout.addRow("api endpoint",self.url_edit)
        self.setLayout(layout)
        self.setWindowTitle("Endpoint")

    def save(self):
        s = dict()
        s["endpoint"] = self.url_edit.text()
        write_settings(s)

    def load(self):
        s = read_settings()
        if "endpoint" in s:
            self.url_edit.setText(s["endpoint"])
        if not self.url_edit.text():
            self.url_edit.setText("https://myvariant.info/v1/variant/")


class SettingsWidget(GroupWidget):
    def __init__(self):
        super().__init__()
        self.page1 = SettingsPage()
        self.add_settings_widget(self.page1)



class MyVariantWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.view = QTreeView()
        self.model = QJsonModel()
        self.view.setModel(self.model)
        self.save_expands = []
        layout = QVBoxLayout()
        layout.addWidget(self.view)
        self.setLayout(layout)

    def save_expand(self):
        print("save expand")
        self.save_expands.clear()
        for index in self.model.persistentIndexList():
            if self.view.isExpanded(index):
                self.save_expands.append(index)

    def load_expand(self):
        print("load expand")
        for index in self.save_expands:
            print(index)
            self.view.setExpanded(index,True)


class MyvariantPlugin(plugin.Plugin):
    Name = "MyVariant.info"
    Description="Appli to display MyVariant.info data"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.view = MyVariantWidget()
        self.net = QNetworkAccessManager()
        self.net.finished.connect(self._on_data_received)


    def get_widget(self):
        return self.view

    def get_settings_widget(self):
        return SettingsWidget()
        

    def on_variant_clicked(self, variant):

        endpoint = read_settings().get("endpoint")

        if endpoint:
            url = endpoint + "{chr}:g.{pos}{ref}>{alt}".format(**variant)
            logging.warning(url)
            request = QNetworkRequest(QUrl(url))
            reply = self.net.get(request)

    def _on_data_received(self, reply: QNetworkReply):
        print("received")
        data = reply.readAll()
        # Convert QByteArray to Python str is cumbersome
        json_data = str(data.data(), encoding='utf-8')
        self.view.model.load(json.loads(json_data))
        self.view.load_expand()
        self.view.save_expand()

if __name__ == "__main__":
    
    import sys 
    app = QApplication(sys.argv)

    plugin = MyvariantPlugin()
    w = plugin.get_widget()
    w.show()
    plugin.on_variant_clicked({"chr":"chr1", "pos":976514,"ref":"C","alt":"A"})

    app.exec_()