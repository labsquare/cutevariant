"""Plugin to Display genotypes variants 
"""
import sqlite3
from tarfile import RECORDSIZE
from tracemalloc import start
import typing
from functools import partial
import time
import copy
import re
import os
import tempfile

# Qt imports
from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtWebEngineWidgets import *
from PySide6.QtWebEngineCore import *

# Custom imports
from cutevariant.core import sql, command
from cutevariant.core.reader import BedReader
from cutevariant.gui import plugin, FIcon, style
from cutevariant.commons import DEFAULT_SELECTION_NAME

from dash import Dash, html, dcc
# import dash as dcc
# import dash as html
import json
import dash_bio as dashbio
# from OpenGL.GL import *
# from OpenGL.GLU import *
import threading
import urllib.request
import multiprocessing
import requests
import signal

from cutevariant.gui.style import (
    GENOTYPE,
    CLASSIFICATION,
    SAMPLE_CLASSIFICATION,
    SAMPLE_VARIANT_CLASSIFICATION,
)

from pycircos import *
import matplotlib.pyplot as plt
import collections
import webview



def get_variants(self,conn: sqlite3.Connection):
    """Get variants"""

    # Available fields
    table_columns_variants=sql.get_table_columns(self.conn,"variants")
    table_columns_annotations=sql.get_table_columns(self.conn,"annotations")
    
    # Wanted fields
    fields_wanted={"id", "chr", "pos", "ref", "alt", "classification", "is_snp", "is_indel", "svtype", "event", "end", "mateid", "meinfo", "svlen"}
    fields={}
    for field in fields_wanted:
        if field in table_columns_variants or field in table_columns_annotations:
            fields[field]=1
    
    # Filters
    filters=self.mainwindow.get_state_data("filters")

    # Source
    source=self.mainwindow.get_state_data("source")

    # Results
    results = {}
    for record in sql.get_variants(self.conn, fields, source, filters, limit=1000):
        results[record["id"]] = dict(record)

    return results


# def run_dash(data, layout):

#     data = [
     
#             {'x': [1, 2, 3], 'y': [4, 1, 2], 'type': 'bar', 'name': 'SF'},
#             {'x': [1, 2, 3], 'y': [2, 4, 5], 'type': 'bar', 'name': u'Montréal'},
#         ]
#     layout = {
#         'title': 'Dash Data Visualization'
#     }
#     app = dash.Dash()

#     data = [
    
#         {'x': [1, 2, 3], 'y': [4, 1, 2], 'type': 'bar', 'name': 'SF'},
#         {'x': [1, 2, 3], 'y': [2, 4, 5], 'type': 'bar', 'name': u'Montréal'},
#     ]
#     layout = {
#         'title': 'Dash Data Visualization'
#     }
#     app = dash.Dash()
#     app.layout = html.Div(children=[
#         html.H1(children='Hello Dash'),
#         html.Div(children='''
#             Dash: A web application framework for Python.
#         '''),
#         dcc.Graph(
#             id='example-graph',
#             figure={
#                 'data': data,
#                 'layout': layout
#             })
#         ])


class Circos2View(QRunnable):

    def __init__(self, *args, **kwargs):
        #super(Circos2View, self).__init__()
        super().__init__()
        self.args = args
        self.kwargs = kwargs
        #self.run()
        print("TRUC1")
        #self.run()
        

    @Slot()  # QtCore.Slot
    def run(self):
        
        # def run_server_dash():
        #     self.app.run_server(debug=False, port=8016, host='127.0.0.1')

        data = [
     
            {'x': [1, 2, 3], 'y': [4, 1, 2], 'type': 'bar', 'name': 'SF'},
            {'x': [1, 2, 3], 'y': [2, 4, 5], 'type': 'bar', 'name': u'Montréal'},
        ]
        layout = {
           'title': 'Dash Data Visualization'
        }
        self.app = Dash()
        self.app.layout = html.Div(children=[
            html.H1(children='Hello Dash on CuteVariant!!!'),
            html.Div(children='''
                Dash: A web application framework for Python3.
            '''),
            dcc.Graph(
                id='example-graph',
                figure={
                    'data': data,
                    'layout': layout
                })
            ])

        # self.server_process = multiprocessing.Process(target=run_server_dash)
        # self.server_process.start()

        #self.app.run_server(debug=False, port=8016, host='127.0.0.1')
        self.app.run_server(debug=False, port=8050, host='0.0.0.0')
        #app.run_server(debug=False)
    
    def shutdown(self):
        self.app.shutdown_server()
        return 'Server shutting down...'

    def terminate(self):
        #self.app.shutdown_server()
        os.kill(os.getpid(), signal.SIGTERM)
        #requests.post('http://127.0.0.1:8016/shutdown')
        #sys.exit()
        return 'Server shutting down...'
    
    
#class MainWidget(QWidget):plugin.PluginWidget
class Circos2Widget(plugin.PluginWidget):
    
    ENABLE = True
    REFRESH_STATE_DATA = {"current_variant","filters","source"}

    def __init__(self,parent = None):
        super().__init__(parent)
        
        # Circos2View Dash Worker
        self.threadpool = QThreadPool()
        self.worker = Circos2View() # Any other args, kwargs are passed to the run function
        self.threadpool.start(self.worker) 

        # QWebEngineView
        self.browser = QWebEngineView()
        #self.browser.settings().setAttribute(QWebEngineSettings.WebGLEnabled, True)
        #self.browser.setUrl(QUrl("http://127.0.0.1:8016/"))
        self.browser.setUrl(QUrl("http://0.0.0.0:8050/"))
        #self.browser.setUrl(QUrl("http://www.google.fr"))
        # self.browser.load(QUrl("http://www.google.fr"))
        # self.browser.show()
        #QDesktopServices.openUrl("http://127.0.0.1:8016/")
        #self.D = QDesktopServices()
        #self.D.openUrl("http://127.0.0.1:8016/")

        # DashView
        #self.view = DashView(parent)


        # Buttons and Edit
        self.btn = QPushButton('Button', self)
        self.btn2 = QPushButton('Button2', self)
        self.btn.resize(self.btn.sizeHint())
        self.edit = QLineEdit("Write my name here")
        
        # Create layout and add widgets
        self.vlayout = QVBoxLayout()
        self.vlayout.addWidget(self.btn)
        self.vlayout.addWidget(self.browser)
        #self.vlayout.addWidget(self.view)
        self.vlayout.addWidget(self.edit)
        self.vlayout.addWidget(self.btn2)
        #self.btn.clicked.connect(self.greetings)
        self.btn.clicked.connect(self.change_url)

        self.setLayout(self.vlayout)

        #self.exit=QAction("Exit Application",shortcut=QKeySequence("Ctrl+q"),triggered=lambda:self.exit_app)
   

    def closeEvent(self, event):
        # do stuff
        self.worker.terminate()
        event.accept() # let the window close
        #sys.exit()
        # if can_exit:
            
        # else:
        #     event.ignore()
    
    def close(self):
        print("Close Dash server...") #verification of shortcut press
        self.worker.terminate()
        self.close()

    # Greets the user
    def greetings(self):
        print ("Hello %s" % self.edit.text())
        self.show()

    def change_url(self):
        self.D.openUrl("http://www.google.fr/")
        #self.show()


if __name__ == "__main__":

    import sqlite3
    import sys
    from PySide6.QtWidgets import QApplication

    data = [
        {'x': [1, 2, 3], 'y': [4, 1, 2], 'type': 'bar', 'name': 'SF'},
        {'x': [1, 2, 3], 'y': [2, 4, 5], 'type': 'bar', 'name': u'Montréal'},
    ]

    layout = {
        'title': 'Dash Data Visualization'
    }

    #threading.Thread(target=run_dash, args=(data, layout), daemon=True).start()
    app = QApplication(sys.argv)
    #conn = sqlite3.connect("/home/sacha/test.db")
    conn = sql.get_sql_connection("database.db")
    conn.row_factory = sqlite3.Row
    view = Circos2Widget() #(conn=conn)
    #view.on_open_project(conn)

    view.show()

    app.exec()

    # threading.Thread(target=run_dash, args=(data, layout), daemon=True).start()
    # app = QtWidgets.QApplication(sys.argv)
    # mainWin = MainWindow()
    # mainWin.show()
    # sys.exit(app.exec_())