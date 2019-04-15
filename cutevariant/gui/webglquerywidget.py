from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWebEngineWidgets import QWebEngineView, QWebEnginePage


from cutevariant.gui.ficon import FIcon


from .plugin import QueryPluginWidget
from cutevariant.core import Query
from cutevariant.core import sql
from collections import Counter



class WebGLQueryWidget(QueryPluginWidget):
    def __init__(self, parent = None):
        super().__init__(parent)
        self.setWindowTitle("web GL")


        self.view = QWebEngineView()
        self.view.setHtml("""
            <!DOCTYPE html>
            <html lang="en">
            <head>
              <meta charset="utf-8">
             <script src="https://cdn.rawgit.com/arose/ngl/v2.0.0-dev.31/dist/ngl.js"></script> 
            </head>
            <body>
              
            <style type="text/css">
            * { margin: 0; padding: 0; }
            html, body { width: 100%; height: 100%; overflow: hidden; }
            </style>

            <div id="viewport" style="width:100%; height:100%;"></div>

            <script>
              // Create NGL Stage object
            var stage = new NGL.Stage( "viewport" );

            // Handle window resizing
            window.addEventListener( "resize", function( event ){
                stage.handleResize();
            }, false );


            // Load PDB entry 1CRN
            stage.loadFile( "rcsb://1crn", { defaultRepresentation: true } );
            </script>



            </body>
            </html>

            """)

        #self.view.loadFinished.connect(self.loaded)



        layout = QVBoxLayout()
        layout.setContentsMargins(0,0,0,0)
        layout.addWidget(self.view)

        self.setLayout(layout)


    def loaded(self):
        print("FINISHED!!!!!!!!!!!!!!!!!!!")


    def setQuery(self, query: Query):

        self.query = query 

       



    def getQuery(self):
        return self.query  # Useless , this widget is query read only 

