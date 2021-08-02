"""Plugin to show all characteristics of a selected variant

VariantInfoWidget is showed on the GUI, it uses VariantPopupMenu to display a
contextual menu about the variant which is selected.
VariantPopupMenu is also used in viewquerywidget for the same purpose.
"""
from logging import DEBUG

# Qt imports
from PySide2.QtCore import *
from PySide2.QtWidgets import *
from PySide2.QtGui import *
from PySide2.QtWebEngineWidgets import *

# Custom imports
from cutevariant.gui import FIcon, style
from cutevariant.core import sql, get_sql_connection
from cutevariant.gui.plugin import PluginWidget
from cutevariant import commons as cm

from cutevariant.gui.widgets import DictWidget


from cutevariant.gui.widgets.qjsonmodel import QJsonModel, QJsonTreeItem


class NGLWidget(QWebEngineView):

    TEMPLATE = """

    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="utf-8">
      <style>
    *{
  margin: 0;
  padding: 0;
}
      </style>
    </head>
    <body>


      <script src="https://cdnjs.cloudflare.com/ajax/libs/ngl/2.0.0-dev.39/ngl.js"></script>

      <div id="viewport" style="width:{WIDTH}px; height:{HEIGHT}px;"></div>
    </body>
    </html>

    """

    def __init__(self):

        super().__init__()

        self.filename = "rcsb://1CRN"
        self.representation = "licorice"
        self.position = 4
        self.spin = True
        self.settings().setAttribute(
            QWebEngineSettings.LocalContentCanAccessRemoteUrls, True
        )

        self.settings().setAttribute(QWebEngineSettings.LocalStorageEnabled, True)
        self.settings().setAttribute(QWebEngineSettings.FullScreenSupportEnabled, True)

        self.resize(640, 500)
        self.loadFinished.connect(self.create_stage)

        self.reset()

    def reset(self):

        HTML = self.TEMPLATE.replace("{WIDTH}", str(self.rect().width()))
        HTML = HTML.replace("{HEIGHT}", str(self.rect().height()))

        with open("/tmp/test.html", "w") as file:
            file.write(HTML)

        self.load(QUrl.fromLocalFile("/tmp/test.html"))

    def create_stage(self):

        self.page().runJavaScript(
            """
            var stage = new NGL.Stage("viewport");

        var schemeId = NGL.ColormakerRegistry.addSelectionScheme([
            ["red", "*"]], "red");
        var schemeId1 = NGL.ColormakerRegistry.addSelectionScheme([
            ["blue", "*", ]], "blue");

        function create_representation_scheme(component, scale, representation, position, colorScheme, opacity = 1){
            component.addRepresentation(representation, {
                    sele: position,
                    scale : scale,
                    colorScheme: colorScheme,
                    opacity : opacity
                });
            return component
            };

            """
        )

    def load_mol(self, protein="rcsb://1crn"):

        self.page().runJavaScript(
            """

        position_prot = "%s";
        representation_prot = "%s";

        function structure_representation(component, position = position_prot, representation = representation_prot) {
                // bail out if the component does not contain a structure
            if (component.type !== "structure") return;
                create_representation_scheme(component, "1", representation, "*", schemeId);
                create_representation_scheme(component, "1", representation, position, schemeId1);
                create_representation_scheme(component, "10", representation, position, schemeId1, 0.5);
                
                component.autoView(position, 2000);
            };
            stage.removeAllComponents();
            stage.loadFile("%s").then(structure_representation);
            stage.setSpin(%s);
            stage.handleResize();

            """
            % (
                self.position,
                self.representation,
                protein,
                "true" if self.spin else "false",
            )
        )


class NglViewWidget(PluginWidget):
    """Plugin to show all annotations of a selected variant"""

    ENABLE = True
    REFRESH_STATE_DATA = {"current_variant"}

    def __init__(self, parent=None):
        super().__init__(parent)

        self.view = NGLWidget()

        self.button = QPushButton("CHARGER")
        self.vlayout = QVBoxLayout()
        # self.vlayout.addWidget(self.button)
        self.vlayout.addWidget(self.view)

        self.setLayout(self.vlayout)

    def on_open_project(self, conn):
        self.conn = conn

    def on_refresh(self):

        """Set the current variant by the variant displayed in the GUI"""

        from random import randint

        self.view.position = randint(1, 20)
        self.view.load_mol()


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)

    # conn = get_sql_connection("/home/schutz/Dev/cutevariant/examples/test.db")
    w = NglViewWidget()
    w.show()

    app.exec_()
