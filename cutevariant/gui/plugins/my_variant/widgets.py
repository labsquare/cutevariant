from cutevariant.gui import plugin, FIcon, network
from cutevariant.core import sql
from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *

from PySide2.QtNetwork import QNetworkRequest, QNetworkReply
from cutevariant.gui.plugins.my_variant.qjsonmodel import QJsonModel

import json
import logging

class MyVariantWidget(plugin.PluginWidget):
    def __init__(self):
        super().__init__()
        self.view = QTreeView()
        self.search_edit = QLineEdit()
        self.model = QJsonModel()
        self.proxy_model = QSortFilterProxyModel()
        self.proxy_model.setSourceModel(self.model)
        #self.proxy_model.setRecursiveFilteringEnabled(True)
        self.view.setAlternatingRowColors(True)
        self.view.setModel(self.proxy_model)
        self.save_expands = []
        layout = QVBoxLayout()
        layout.addWidget(self.view)
        layout.addWidget(self.search_edit)
        self.setLayout(layout)
     
        self.net = network.get_network_manager()
        self.net.finished.connect(self._on_data_received)

        self.search_edit.textChanged.connect(self.proxy_model.setFilterRegExp)


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



    def on_variant_changed(self, variant):
        """ overrided from Plugin Widget """ 

        print(variant)
        endpoint = "https://myvariant.info/v1/variant/"

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
        self.model.load(json.loads(json_data))
        #self.view.load_expand()
        #self.view.save_expand()
        self.view.expandAll()


if __name__ == "__main__":
    import sys 
    import sqlite3

    app = QApplication(sys.argv)

    view = MyVariantWidget()
    view.on_variant_changed({"chr":3,"pos":324,"ref":"A","alt":"T"})
    view.show()

    app.exec_()


