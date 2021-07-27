import PySide2
from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWebEngineWidgets import *
import sys
import os


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
        <div id="viewport" style="width:0px; height:0px;"></div>
    </body>
    </html>

    """

    def __init__(self) -> None:
        """Init state
        filename : str file's name
        representation : str type of the geometry to show the prot
        position : int amino acid index to focus on
        spin : str for an js bool, if "true" rotate the protein
        mol_loaded : bool is there a mol loaded
        sized : bool True if the window has been resized once
        """

        super().__init__()

        self.filename = "rcsb://1CRN"
        self.representation = ""
        self.position = 1
        self.spin = "false"
        self.mol_loaded = False
        self.sized = False
        self.setHtml(self.TEMPLATE)
        self.settings().setAttribute(
            QWebEngineSettings.LocalContentCanAccessRemoteUrls, True
        )
        self.settings().setAttribute(QWebEngineSettings.LocalStorageEnabled, True)
        self.settings().setAttribute(QWebEngineSettings.FullScreenSupportEnabled, True)
        self.settings().setAttribute(
            QWebEngineSettings.LocalContentCanAccessFileUrls, True
        )

        self.loadFinished.connect(self.load_tools)
        self.loadFinished.connect(self.set_window_size)
        self.page().setBackgroundColor(QColor("white"))

    def set_window_size(self, width: int = 500, height: int = 500) -> None:
        """set to the window size
        Args:
            width (int, optional): width in pixel. Defaults to 0.
            height (int, optional): height in pixel. Defaults to 0.
        """

        self.page().runJavaScript(
            f"""
            
            document.getElementById('viewport').style.width = "{width}px";
            document.getElementById('viewport').style.height = "{height}px";

            """
        )

    def set_position(self, value: int) -> None:
        """set position to the given value
        Args:
            value (int): value to set
        """

        self.position = value

    def load_tools(self) -> None:
        """load constant for js"""

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
        print("loadind done")

    def load_mol(self, protein: str = "rcsb://1crn") -> None:
        """load molecule
        Args:
            protein (str, optional): choose file to give. Defaults to "rcsb://1crn".
        """
        self.page().runJavaScript(
            """

            stage.removeAllComponents();
            stage.loadFile("rcsb://1crn").then(function (component) {
            component.addRepresentation("licorice");
            component.autoView();


            });
            """
        )

        self.mol_loaded = True

    def main_view(self) -> None:
        """set to the global camera"""

        self.page().runJavaScript(
            """
            stage.autoView(800)

        """
        )

    @classmethod
    def bool_python_to_js(cls, pythonbool: bool) -> bool:
        """translate bool prom python to js
        Args:
            pythonbool (bool): boolean to translate

        Returns:
            bool: a js bool
        """

        if pythonbool:
            return "true"
        else:
            return "false"


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        """init MainWindow"""
        super().__init__()

        self.view = NGLWidget()
        self.setCentralWidget(self.view)

        self.combo = QComboBox()
        self.combo.addItems(
            [
                "licorice",
                "ball+stick",
                "surface",
                "cartoon",
                "axes",
                "backbone",
                "hyperball",
            ]
        )
        self.combo.currentTextChanged.connect(self.update_combobox)

        self.toolbar = self.addToolBar("toolbar")
        self.toolbar.setMovable(False)
        self.toolbar2 = self.addToolBar("toolbar2")
        self.toolbar2.setAllowedAreas(Qt.LeftToolBarArea)
        self.toolbar2.setFloatable(False)

        action = self.toolbar.addAction("Load")
        action.triggered.connect(self.on_charger)

        resizeaction = self.toolbar.addAction("resize")
        resizeaction.triggered.connect(self.resize)

        cameraaction = self.toolbar.addAction("global view")
        cameraaction.triggered.connect(self.view.main_view)

        self.spin = QCheckBox("spin")
        self.spin.stateChanged.connect(self.update_spin)

        self.textpos = QLabel("position")
        self.selectpos = QLineEdit("1")
        self.selectpos.setFixedSize(80, 15)

        self.toolbar2.addWidget(self.combo)
        self.toolbar2.addWidget(self.spin)
        self.toolbar2.addWidget(self.textpos)
        self.toolbar2.addWidget(self.selectpos)

    def on_charger(self) -> None:
        """set the correct value and load the molecule"""
        self.view.position = self.selectpos.text()
        self.view.representation = self.combo.currentText()
        if not (self.view.sized):
            self.resize()
        self.view.load_mol()

    def update_spin(self) -> None:
        """update the spin value and refresh"""
        self.view.spin = self.spin.isChecked()
        self.view.spin = NGLWidget.bool_python_to_js(self.view.spin)
        if self.view.mol_loaded:
            self.on_charger()

    def update_combobox(self) -> None:
        """update the spin value and refresh"""
        self.view.representation = self.combo.currentText()
        if self.view.mol_loaded:
            self.on_charger()

    def resize(self) -> None:
        """Set the view into the size of the window"""
        width = self.size().width()
        height = self.size().height()
        self.view.set_window_size(width, height)
        if self.view.mol_loaded:
            self.on_charger()
        if not (self.view.sized):
            self.view.sized = True


if __name__ == "__main__":

    app = QApplication(sys.argv)

    w = MainWindow()
    w.show()

    app.exec_()
