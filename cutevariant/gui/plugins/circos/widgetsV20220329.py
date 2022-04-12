"""Plugin to Display genotypes variants 
"""
import typing
from functools import partial
import time
import copy
import re

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



from pycircos import *
import matplotlib.pyplot as plt



#class CircosView(pycircos.Gcircle):
#class CircosView(Gcircle):
class CircosView(QPixmap):
    def __init__(self, parent=None):
        super().__init__()

        #self=
        self.im = QPixmap("/Users/lebechea/BIOINFO/git/circos.jpg")      
        #pixmap.scaled(100, 100)                                                                                                   
        #self.lbl = QLabel(im)                                                                                                                 
        #self.lbl.setPixmap(im)

        #self.im = QPixmap("/Users/lebechea/BIOINFO/git/image.jpg")
        #self.im = label.setpixmap("monimage.png")
        #self.im = QPixmap()
        #self.label = QLabel()
        #self.label = setpixmap("monimage.png")
        #self.label.setPixmap(self.im)
        #self.label.setPixmap("/Users/lebechea/BIOINFO/git/image.jpg")
        #self.label.setPixmap(QPixmap("/Users/lebechea/BIOINFO/git/image.jpg"))

        # self.grid = QGridLayout()
        # self.grid.addWidget(self.label,1,1)
        # self.setLayout(self.grid)

        #self.setGeometry(50,50,320,200)
        #self.setWindowTitle("PyQT show image")
        #self.show()

        #self = pycircos.Gcircle


    # def set_position(self, location):

    #     self.page().runJavaScript(
    #         f"""

    #         $(".igv-search-input").val('{location}')
    #         $(".igv-search-icon-container").trigger("click")

    #         """
    #     )

    def get_figure(self):

        return self.im


class CircosWidget(plugin.PluginWidget):
    """Plugin to show all annotations of a selected variant"""

    ENABLE = True
    REFRESH_STATE_DATA = {"current_variant"}

    def __init__(self, parent=None):
        super().__init__(parent)

        #im = QPixmap("/Users/lebechea/BIOINFO/git/image.gif")
        # pixmap = QPixmap("/Users/lebechea/BIOINFO/git/circos.jpg")      
        # pixmap.scaled(100, 100)   
        #          
        #pixmap = QPixmap("/Users/lebechea/BIOINFO/git/circos.jpg")  
        pixmap = CircosView()                                                                                     
        lbl = QLabel(self)                                                                                                                 
        lbl.setPixmap(pixmap.get_figure())

        #image=CircosView()
        
        self.vlayout = QVBoxLayout()
        #self.vlayout.addWidget(self.view.label)
        #self.vlayout.addWidget(lbl)
        self.vlayout.addWidget(lbl)
        #self.vlayout.addWidget(self.figure)
        self.setLayout(self.vlayout)
        self.resize(200, 300)

        #self.show()

    def on_refresh(self):
        variant = self.mainwindow.get_state_data("current_variant")
        variant = sql.get_variant(self.mainwindow.conn, variant["id"])

        chrom = variant["chr"]
        pos = variant["pos"]

        location = f"{chrom}:{pos}"

        #self.view.set_position(location)


if __name__ == "__main__":

    import sqlite3
    import sys
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    conn = sqlite3.connect("/home/sacha/test.db")
    conn.row_factory = sqlite3.Row

    view = CircosWidget()
    view.on_open_project(conn)

    view.show()

    app.exec()
