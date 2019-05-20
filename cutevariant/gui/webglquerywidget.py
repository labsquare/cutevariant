"""Proof of concept to display the 3D structure of a protein in a WebGL accelerated widget"""
# Qt imports
from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWebEngineWidgets import QWebEngineView

# Custom imports
from .plugin import QueryPluginWidget
from cutevariant.core import Query


class WebGLQueryWidget(QueryPluginWidget):
    """Display the 3D structure of a protein in a WebGL accelerated widget"""

    def __init__(self, protein_reference="1crn", parent=None):
        """Display the 3D structure of the given protein"""
        super().__init__(parent)
        self.setWindowTitle("web GL")

        self.view = QWebEngineView()
        # self.view.loadFinished.connect(self.loaded)
        self.view.setHtml(
            """
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

              // Load PDB entry
              stage.loadFile( "rcsb://6J3G", { defaultRepresentation: true } );
            </script>
            </body>
            </html>
            """
            
        )

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.view)

        self.setLayout(layout)
        self._query = None

    @property
    def query(self):
        return self._query  # Useless , this widget is query read only

    @query.setter
    def query(self, query: Query):
        self._query = query

    def loaded(self):
        print("FINISHED!!!!!!!!!!!!!!!!!!!")
