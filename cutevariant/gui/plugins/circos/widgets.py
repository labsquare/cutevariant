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

from cutevariant.gui.style import (
    GENOTYPE,
    CLASSIFICATION,
    SAMPLE_CLASSIFICATION,
    SAMPLE_VARIANT_CLASSIFICATION,
)

from pycircos import *
import matplotlib.pyplot as plt
import collections


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


#class CircosView(pycircos.Gcircle):
#class CircosView(Gcircle):
class CircosView(QPixmap):
    def __init__(self, conn=None, parent=None):
        super().__init__()
        self.conn = conn

        self.im = QPixmap() 
        self.im.scaled(100,100)

        self.create_figure(conn=self.conn, variants={})

    def get_figure(self):

        return self.im

    def create_figure(self,conn=None, variants={}):

        # list of contigs, classification
        contig_list = {}
        classification_list = {}
        if variants:
            for variant in variants:
                if re.match("^chr", variants[variant]["chr"]):
                    chr=variants[variant]["chr"]
                else:
                    chr = "chr"+variants[variant]["chr"]
                #contig_list[variants[variant]["chr"]]=1
                contig_list[chr]=1
                classification_list[variants[variant]["classification"]]=variants[variant]["classification"]


        # Contigs for hg19
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

        # Create Garc and Gcircle
        Garc    = pycircos.Garc
        Gcircle = pycircos.Gcircle
        circle = Gcircle() 


        raxis_max=900
        raxis_window=80
        raxis_padding=10
        raxis_current=raxis_max
        raxis_previous=raxis_max


        # Label
        #######

        record={}
        garc   = Garc(arc_id="label", record=record, interspace=0, linewidth=0, 
              facecolor="#FFFFFF00", raxis_range=(0,10), 
              label="Cicos", label_visible=True)

        circle.add_garc(garc)
        circle.set_garcs()

        
        # Contigs
        #########

        arcdata_dict = collections.defaultdict(dict)

        raxis_current=raxis_previous
        raxis_bottom=raxis_current-raxis_window
        raxis_top=raxis_current
        raxis_previous=raxis_current-raxis_window-raxis_padding

        #print(contigs)
        #print(contig_list)

        if contigs:

            for chr in contigs:
                #print("chr_1:"+chr)
                if not re.match("^chr", chr):
                    chr = "chr"+chr
                #print("chr_2:"+chr)
                #if chr in contig_list or "chr"+chr in contig_list: 
                if chr in contig_list:
                    #print("chr_3:"+chr)
                    if re.match("^chr", chr):
                        name = chr
                    else:
                        name = "chr"+chr
                    #name   = chr
                    length = int(contigs[chr])
                    arcdata_dict[name]["colors"] = "#BBBBBB"
                    arc    = Garc(arc_id=name, size=length, interspace=3, raxis_range=(raxis_bottom,raxis_top), labelposition=60, facecolor=arcdata_dict[name]["colors"], label_visible=True)
                    circle.add_garc(arc) 
            
        circle.set_garcs(start=0, end=360) 


        # SNV and InDel
        ###############

        #values_all = {}
        value_all_snv = []
        value_all_indel = []
        value_all_sv = []
        #values_all = {}
        circles = {}
        circles["snv"] = collections.defaultdict(dict)
        circles["indel"] = collections.defaultdict(dict)
        circles["sv"] = collections.defaultdict(dict)
        circles["bnd"] = collections.defaultdict(dict)


        if variants:

            for variant in variants:

                # ALL variants
                #print("Variant type: ALL")
                if re.match("^chr", variants[variant]["chr"]):
                    name = variants[variant]["chr"]
                else:
                    name = "chr"+variants[variant]["chr"]
                #print("chr:"+name)
                start = int(variants[variant]["pos"])
                end = int(variants[variant]["pos"])
                mid = int(variants[variant]["pos"])
                classification = variants[variant]["classification"]
                color=style.CLASSIFICATION[classification].get("color")
                value = float(classification)+abs(min(classification_list))+1
                value_all_snv.append(value)
                width=1
                if name not in circles["snv"]:
                    circles["snv"][name]["positions"] = []
                    circles["snv"][name]["values"] = []
                    circles["snv"][name]["colors"] = [] 
                    circles["snv"][name]["widths"] = []
                circles["snv"][name]["positions"].append(mid) 
                circles["snv"][name]["values"].append(value)
                circles["snv"][name]["widths"].append(width)
                circles["snv"][name]["colors"].append(color)

                # SV
                if "svtype" in variants[variant] and variants[variant]["svtype"] != None and 1:

                    svtype=variants[variant]["svtype"]
                    pos = variants[variant]["pos"]
                    classification = variants[variant]["classification"]
                    
                    found=""
                    svlen=0
                    svend=0

                    #print("Variant type: SV ("+svtype+")")

                    if re.match("^chr", variants[variant]["chr"]):
                        name = variants[variant]["chr"]
                    else:
                        name = "chr"+variants[variant]["chr"]

                    if "end" in variants[variant] and variants[variant]["end"] != None:

                        svend = int(variants[variant]["end"])

                        start, end = min([int(pos), int(svend)]), max([int(pos), int(svend)])

                        mid = (pos-start)/2
                        value = float(classification)+abs(min(classification_list))+1
                        value_all_sv.append(value)
                        width=end-start

                        found="sv"

                    
                    elif "svlen" in variants[variant] and variants[variant]["svlen"] != None:
                    
                        svlen = int(variants[variant]["svlen"])

                        if svlen > 0 :
                            start = pos
                            end = pos+svlen
                        else:
                            start = pos+svlen
                            end = pos

                        mid = (pos-start)/2
                        value = float(classification)+abs(min(classification_list))+1
                        value_all_sv.append(value)
                        width=end-start

                        found="sv"

                    elif "svtype" in variants[variant] and variants[variant]["svtype"] == "BND":

                        ref=variants[variant]["ref"]
                        alt=variants[variant]["alt"]
                        pos=variants[variant]["pos"]

                        start = pos
                        end = pos

                        if end in variants[variant]:
                            svend = int(variants[variant]["end"])
                            start, end = min([int(pos), int(svend)]), max([int(pos), int(svend)])

                        if svlen in variants[variant]:
                            svlen = int(variants[variant]["svlen"])
                            if svlen > 0 :
                                start = pos
                                end = pos+svlen
                            else:
                                start = pos+svlen
                                end = pos

                        minlength=2000000

                        svlength1=end-start
                        if svlength1 < minlength:
                            svlength1 = minlength

                        end=start+svlength1

                        for i in re.split('\]|\[',alt):
                            if ref != i and i != "":
                                chr2=re.split(':',i)[0]
                                pos2=re.split(':',i)[1]

                        if re.match("^chr", chr2):
                            name2 = chr2
                        else:
                            name2 = "chr"+chr2

                        # TODO
                        # Find the other connected variant to find length and classification/value
                        # svlength2 = minlength

                        name1  = name     
                        start1 = int(start)
                        end1   = int(end)
                        name2  = name2     
                        start2 = int(pos2)
                        end2   = int(pos2)+minlength
                        source = (name1, start1, end1, 630)
                        destination = (name2, start2, end2, 630)
                        if name1 in contig_list and name2 in contig_list: 
                            circles["bnd"][name1]["name1"] = name1
                            circles["bnd"][name1]["start1"] = start1
                            circles["bnd"][name1]["end1"] = end1
                            circles["bnd"][name1]["name2"] = name2
                            circles["bnd"][name1]["start2"] = start2
                            circles["bnd"][name1]["end2"] = end2
                            circles["bnd"][name1]["color"] = color
                    
                        found="bnd"

                    if found == "sv":

                        if name not in circles["sv"]:
                            circles["sv"][name]["positions"] = []
                            circles["sv"][name]["values"] = []
                            circles["sv"][name]["colors"] = [] 
                            circles["sv"][name]["widths"] = []
                        circles["sv"][name]["positions"].append(mid) 
                        circles["sv"][name]["values"].append(value)
                        circles["sv"][name]["widths"].append(width)
                        circles["sv"][name]["colors"].append(style.CLASSIFICATION[classification].get("color"))

                
            # snv/indel
            raxis_current=raxis_previous
            raxis_bottom=raxis_current-raxis_window
            raxis_top=raxis_current
            raxis_previous=raxis_current-raxis_window-raxis_padding

            if len(value_all_indel):
                vmin_indel, vmax_indel = min(value_all_indel), max(value_all_indel) 
            else:
                vmin_indel = 0
                vmax_indel = 1
            
            if len(value_all_snv):
                vmin_snv, vmax_snv = min(value_all_snv), max(value_all_snv) 
            else:
                vmin_snv = 0
                vmax_snv = 1
            
            vmin, vmax = min([vmin_indel, vmin_snv]), max([vmax_indel, vmax_snv])

            if vmin == vmax:
                vmax=vmin+1

            if len(circles["indel"]):               
                for key in circles["indel"]:
                    circle.scatterplot(key, data=circles["indel"][key]["values"], positions=circles["indel"][key]["positions"],
                            rlim=[vmin-0.05*abs(vmin), vmax+0.05*abs(vmax)], raxis_range=(raxis_bottom,raxis_top), facecolor=circles["indel"][key]["colors"], spine=True) 

            if len(circles["snv"]):
                for key in circles["snv"]:
                    circle.scatterplot(key, data=circles["snv"][key]["values"], positions=circles["snv"][key]["positions"],
                            rlim=[vmin-0.05*abs(vmin), vmax+0.05*abs(vmax)], raxis_range=(raxis_bottom,raxis_top), facecolor=circles["snv"][key]["colors"], spine=True) 

            # sv
            raxis_current=raxis_previous
            raxis_bottom=raxis_current-raxis_window
            raxis_top=raxis_current
            raxis_previous=raxis_current-raxis_window-raxis_padding

 
            if len(circles["sv"]):
                #print(circles["sv"])
                vmin, vmax = min(value_all_sv), max(value_all_sv) 
                if vmin == vmax:
                    vmax=vmin+1
                for key in circles["sv"]:
                    circle.heatmap(key, data=circles["sv"][key]["values"], positions=circles["sv"][key]["positions"], width=circles["sv"][key]["widths"], 
                            raxis_range=(raxis_bottom,raxis_top), vmin=vmin, vmax=vmax, cmap=plt.cm.viridis) 

            raxis_current=raxis_previous
            raxis_bottom=raxis_current-raxis_window
            raxis_top=raxis_current
            raxis_previous=raxis_current-raxis_window-raxis_padding


            if len(circles["bnd"]):
                for key in circles["bnd"]:
                    source = (circles["bnd"][key]["name1"], circles["bnd"][key]["start1"], circles["bnd"][key]["end1"], raxis_current)
                    destination = (circles["bnd"][key]["name2"], circles["bnd"][key]["start2"], circles["bnd"][key]["end2"], raxis_current)
                    #destination = (name2, start2, end2, 630)
                    circle.chord_plot(source, destination, facecolor=circles["bnd"][key]["color"])



        # Create image
        ##############

        new_file, path = tempfile.mkstemp()
        circle.figure.savefig(path,format="svg")
        self.im = QPixmap(path) 
        os.remove(path)



class CircosWidget(plugin.PluginWidget):
    """Plugin to show all annotations of a selected variant"""

    ENABLE = True
    REFRESH_STATE_DATA = {"current_variant","filters","source"}

    def __init__(self, conn=None, parent=None):
        super().__init__(parent)
        self.conn = self.mainwindow.conn

        self.pixmap = CircosView(conn=self.conn)      
        #self.pixmap.scaled(100, 100)                                                                                
        self.lbl = QLabel(self)                                                                                                                 
        self.lbl.setPixmap(self.pixmap.get_figure())

        self.vlayout = QVBoxLayout()
        self.vlayout.addWidget(self.lbl)
        self.setLayout(self.vlayout)
        self.resize(200, 300)


    def on_refresh(self):
        variants = get_variants(self,self.conn)
        self.pixmap.create_figure(conn=self.conn,variants=variants)
        self.lbl.setPixmap(self.pixmap.get_figure())


    def on_open_project(self, conn): 
        self.conn = conn

if __name__ == "__main__":

    import sqlite3
    import sys
    from PySide6.QtWidgets import QApplication


    app = QApplication(sys.argv)
    #conn = sqlite3.connect("/home/sacha/test.db")
    conn = sql.get_sql_connection("database.db")
    conn.row_factory = sqlite3.Row
    view = CircosWidget(conn=conn)
    view.on_open_project(conn)

    view.show()

    app.exec()
