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
import collections


def get_variants(conn: sqlite3.Connection):
    """Get variants"""
    results = {}
    for record in conn.execute(
        f"""SELECT `id`, `chr`, `pos`, `ref`, `alt`
            FROM `variants`
            """
    ):
        results[record["id"]] = dict(record)

    print(len(results))
    return results


#class CircosView(pycircos.Gcircle):
#class CircosView(Gcircle):
class CircosView(QPixmap):
    def __init__(self, conn=None, parent=None):
        super().__init__()
        self.conn = conn
        #self.conn = self.mainwindow.conn

        self.path = ""
        self.im = QPixmap(self.path) 
        
        # self.im = QPixmap()
        self.create_figure(conn=self.conn, variants={}, path=self.path)

    def get_figure(self):

        return self.im

    def create_figure(self,conn=None, variants={}, path=1):
    #def create_figure(self, test=1):
        #print(variants)
        #print(path)
        #variants = get_variants(conn)
        #print(self.super().data())
        #variants=get_variants()
        #variants = get_variants(self.conn)

        contigs = {
            "chr1" : "249250621",
            "chr2" : "243199373",
            "chr3" : "198022430",
            "chr4" : "191154276",
            "chr5" : "180915260",
            "chr6" : "171115067",
            "chr7" : "159138663",
            "chr8" : "146364022",
            "chr9" : "141213431",
            "chr10" : "135534747",
            "chr11" : "135006516",
            "chr12" : "133851895",
            "chr13" : "115169878",
            "chr14" : "107349540",
            "chr15" : "102531392",
            "chr16" : "90354753",
            "chr17" : "81195210",
            "chr18" : "78077248",
            "chr19" : "59128983",
            "chr20" : "63025520",
            "chr21" : "48129895",
            "chr22" : "51304566",
            "chrX" : "155270560",
            "chrY" : "59373566"
        }

        Garc    = pycircos.Garc
        Gcircle = pycircos.Gcircle
        
        circle = Gcircle() 

        arcdata_dict = collections.defaultdict(dict)

        for chr in contigs:
            #print(chr)
            #print(contigs[chr])
            #line   = line.rstrip().split(",") 
            name   = chr
            length = int(contigs[chr])
            arcdata_dict[name]["colors"] = "#BBBBBB"
            arc    = Garc(arc_id=name, size=length, interspace=3, raxis_range=(950,1000), labelposition=60, facecolor=arcdata_dict[name]["colors"], label_visible=True)
            circle.add_garc(arc) 
        circle.set_garcs() 

        #scatter plot
        values_all   = [] 
        arcdata_dict = collections.defaultdict(dict)
        # with open("/Users/lebechea/BIOINFO/git/pyCircos/tutorial/sample_data/example_data_point.csv") as f:
        #     f.readline()
        #     for line in f:
        #         line  = line.rstrip().split(",")
        #         name  = line[0]     
        #         start = int(line[1])-1
        #         end   = int(line[2]) 
        #         mid   = (start+end)/2
        #         value = float(line[-1]) 
        #         values_all.append(value) 
        #         if name not in arcdata_dict:
        #             arcdata_dict[name]["positions"] = []
        #             arcdata_dict[name]["values"] = []
        #         arcdata_dict[name]["positions"].append(mid) 
        #         arcdata_dict[name]["values"].append(value)

        # chr,start,end,value1
        # chr1,1769292,1796134,0.339
        # chr1,4881594,5495466,1.005
        # chr1,9076857,21130138,-0.247
        # chr1,27279764,27941507,0.092
        # chr1,28351697,32840519,-0.677
        # chr1,35166605,38111246,0.344
        # chr1,40292931,41985400,0.305
        # chr1,45292238,48455065,0.39
        # chr1,53310920,59664194,-0.053

        #print(variants)

        if variants:

            for variant in variants:
                #print(variant)
                #print(variants[variant]["chr"])
                name = variants[variant]["chr"]
                start = int(variants[variant]["pos"])
                end = int(variants[variant]["pos"])
                mid = int(variants[variant]["pos"])
                value = 1.0
                #print("value")
                #print(value)
                values_all.append(value)
                if name not in arcdata_dict:
                    arcdata_dict[name]["positions"] = []
                    arcdata_dict[name]["values"] = []
                    arcdata_dict[name]["colors"] = [] 
                arcdata_dict[name]["positions"].append(mid) 
                arcdata_dict[name]["values"].append(value)
                arcdata_dict[name]["colors"] = "#BBBBBB"

            #print(values_all)
                
            vmin, vmax = min(values_all), max(values_all) 
            for key in arcdata_dict:
                circle.scatterplot(key, data=arcdata_dict[key]["values"], positions=arcdata_dict[key]["positions"], 
                                rlim=[vmin-0.05*abs(vmin), vmax+0.05*abs(vmax)], raxis_range=(860,940), facecolor="orangered", spine=True) 




        circle.figure.savefig("/Users/lebechea/BIOINFO/git/circos.svg",format="svg")

        path="/Users/lebechea/BIOINFO/git/circos.svg"

        if path==1:
            path="/Users/lebechea/BIOINFO/git/circos1.jpg"
        elif path==2:
            path="/Users/lebechea/BIOINFO/git/circos2.jpg"

        self.im = QPixmap(path) 


# class MonPluginWidget(plugin.PluginWidget):
#     """Widget displaying the list of avaible selections.
#     User can select one of them to update Query::selection
#     """

#     ENABLE = True
#     REFRESH_STATE_DATA = {"current_variant"}
    
#     def on_refresh(self):
#             print(self.mainwindow.get_state_data("current_variant")


class CircosWidget(plugin.PluginWidget):
    """Plugin to show all annotations of a selected variant"""

    ENABLE = True
    REFRESH_STATE_DATA = {"current_variant"}

    def __init__(self, conn=None, parent=None):
        super().__init__(parent)
        #self.conn = conn
        
        print("CONN")
        print(self.mainwindow.conn)
        print(self.conn)
        print(conn)
        self.conn = self.mainwindow.conn

        #im = QPixmap("/Users/lebechea/BIOINFO/git/image.gif")
        # pixmap = QPixmap("/Users/lebechea/BIOINFO/git/circos.jpg")      
        # pixmap.scaled(100, 100)   
        #          
        #pixmap = QPixmap("/Users/lebechea/BIOINFO/git/circos.jpg")  

        self.num=0

        self.pixmap = CircosView(conn=self.conn)                                                                                     
        self.lbl = QLabel(self)                                                                                                                 
        self.lbl.setPixmap(self.pixmap.get_figure())

        #image=CircosView()
        
        self.vlayout = QVBoxLayout()
        #self.vlayout.addWidget(self.view.label)
        #self.vlayout.addWidget(lbl)
        self.vlayout.addWidget(self.lbl)
        #self.vlayout.addWidget(self.figure)
        self.setLayout(self.vlayout)
        self.resize(200, 300)

        #self.show()

    def on_refresh(self):
        #variant = self.mainwindow.get_state_data("current_variant")
        #variant = sql.get_variant(self.mainwindow.conn, variant["id"])

        #print(self.conn)
        variants = get_variants(self.mainwindow.conn)
        #print(variants)

        #chrom = variant["chr"]
        #pos = variant["pos"]
        #location = f"{chrom}:{pos}"

        if self.num!=2:
            self.num=2
        else:
            self.num=1

        #self.view.set_position(location)
        self.pixmap.create_figure(conn=self.conn,variants=variants,path=self.num)
        #self.pixmap.create_figure(self.num)
        self.lbl.setPixmap(self.pixmap.get_figure())


if __name__ == "__main__":

    import sqlite3
    import sys
    from PySide6.QtWidgets import QApplication

    # on_open_project est appelé qd on ouvre un projet
    # tu auras la "conn" en parametre
    # on refresh est appelé qd le plugin a besoin d'etre rafraichi. ( qd un variant change )


    app = QApplication(sys.argv)
    conn = sqlite3.connect("/home/sacha/test.db")
    #conn = sql.get_sql_connection("test.db")
    conn.row_factory = sqlite3.Row
    view = CircosWidget(conn=conn)
    view.on_open_project(conn)

    view.show()

    app.exec()
