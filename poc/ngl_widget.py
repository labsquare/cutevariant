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
        spin : str if "true" rotate the protein
        rock : str if "true" rock the protein
        mol_loaded : bool is there a mol loaded
        sized : bool True if the window has been resized once
        """

        super().__init__()

        self.filename = "rcsb://1crn"
        self.representation = ""
        self.position = 1
        self.colormol = ""
        self.colorAA = ""
        self.spin = False
        self.rock = False
        self.mol_loaded = False
        self.sized = False

        self.settings().setAttribute(
            QWebEngineSettings.LocalContentCanAccessRemoteUrls, True
        )
        self.settings().setAttribute(QWebEngineSettings.LocalStorageEnabled, True)
        self.settings().setAttribute(QWebEngineSettings.FullScreenSupportEnabled, True)

        self.setHtml(self.TEMPLATE)
        self.loadFinished.connect(self.load_tools)
        self.loadFinished.connect(self.set_window_size)
        self.page().setBackgroundColor(QColor("white"))
        ########################################################
        ########################################################
        ########################################################
        # js_code = """

        #  """

        # script = QWebEngineScript()
        # script.setInjectionPoint(QWebEngineScript.DocumentCreation)
        # script.setWorldId(QWebEngineScript.MainWorld)
        # script.setSourceCode(js_code)

        # profile = QWebEngineProfile("NGL")
        # self.page().scripts().insert(script)

    ########################################################
    ########################################################
    ########################################################
    def set_window_size(self, width: int = 0, height: int = 0) -> None:
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

        var stage = new NGL.Stage("viewport", {backgroundColor : "black"});
        var schememol = NGL.ColormakerRegistry.addSelectionScheme([
            ["red", "*"]], "colormol");
        var schemeAA = NGL.ColormakerRegistry.addSelectionScheme([
            ["blue", "*"]], "colorAA");

        function set_colorscheme (scheme, color){
            scheme = NGL.ColormakerRegistry.addSelectionScheme([
                [color, "*"]]);
            return scheme
        };

        function create_representation_scheme(component, scale, representation, position, colorScheme, opacity = 1){
            component.addRepresentation(representation, {
                    sele: position,
                    scale  : scale,
                    colorScheme: colorScheme,
                    opacity : opacity
                });
            return component
            }
    
        """
        )
        print("loading done")

    def load_mol(self) -> None:
        """load molecule"""

        self.page().runJavaScript(
            """

        position_prot = "%s";
        representation_prot = "%s";
        colormol = "%s";
        colorAA = "%s";
        protein = "%s"

        function structure_representation(component, position = position_prot, representation = representation_prot) {
            schememol = set_colorscheme(schememol, colormol);
            schemeAA = set_colorscheme(schemeAA, colorAA);
                // bail out if the component does not contain a structure
            if (component.type !== "structure") return;
                create_representation_scheme(component, "1", representation, "*", schememol);
                create_representation_scheme(component, "1", representation, position, schemeAA);
                create_representation_scheme(component, "10", representation, position, schemeAA, 0.5);
                
                component.autoView(position, 2000);
            };
            stage.removeAllComponents();
            stage.loadFile(protein).then(structure_representation);
            stage.handleResize();
            print(stage.getBox());

            """
            % (
                self.position,
                self.representation,
                self.colormol,
                self.colorAA,
                self.filename,
            )
        )
        print("molecule load")
        self.mol_loaded = True

    def add_component(self, component) -> None:
        """add component to stage

        Args:
            component (Component): component to add
        """
        self.page().runJavaScript(
            f"""
        stage.addComponennt({component})
        """
        )

    def add_component_from_object(self, component) -> None:
        """add component to stage

        Args:
            component (Component): component to add
        """
        self.page().runJavaScript(
            f"""
        stage.addComponenntFromObjetc({component})
        """
        )

    def auto_view(self) -> None:
        """set to the global camera"""

        self.page().runJavaScript(
            """
            stage.autoView(800)
        """
        )

    def default_file_representation(self, component) -> None:
        """set default representation for the component

        Args:
            component (Component): component set at default value
        """
        self.page().runJavaScript(
            f"""
        stage.defaultFileRepresentation({component})
        """
        )

    def dispose(self) -> None:
        """clean stage object"""
        self.page().runJavaScript(
            """stage.dispose()
        """
        )

    def each_component(self, callback) -> None:
        """Iterator over each component and executing the callback

        Args:
            callback ((comp: Component): void) (function): function to execute
        """
        self.page().runJavaScript(
            f"""
            stage.eachComponent({callback})"""
        )

    def each_representation(self, callback) -> None:
        """Iterator over each representation and executing the callback

        Args:
            callback ((reprElem: RepresentationElement, comp: Component): void) (function): function to execute
        """
        self.page().runJavaScript(
            f"""
            stage.eachRepresentation({callback})"""
        )

    def handle_resize(self) -> None:
        """Handle any size-changes of the container element"""
        self.page().runJavaScript(
            f"""
            stage.handleResize()"""
        )

    def laod_file(self, path: str, params: dict = {}) -> any:
        """Load a file onto the stage

        Args:
            path (str): either a URL or an object containing the file data
            parmas (StageLoadingParameter): loading parameters
        """
        self.page().runJavaScript(
            f"""
            stage.laodFile({path}, {params})
        """
        )

    def load_script(self, script: str) -> any:
        """load script object

        Args:
            script (str): or file or blob

        Returns:
            any: [description]
        """
        self.page().runJavaScript(
            f"""
            stage.loadScript({script})
        """
        )

    def log(self, msg: str) -> None:
        """logging

        Args:
            msg (str): or file or blob

        """
        self.page().runJavaScript(
            f"""
            stage.log({msg})
        """
        )

    def measure_clear(self) -> None:
        """clear measure stage"""
        self.page().runJavaScript(
            """
            stage.measureClear()
        """
        )

    def measure_update(self) -> None:
        """update measure stage"""
        self.page().runJavaScript(
            """
            stage.measureUpdate()
        """
        )

    def remove_all_components(self) -> None:
        """remove all components from stage"""
        self.page().runJavaScript(
            """
            stage.removeAllComponents()
        """
        )

    def remove_components(self, component) -> None:
        """remove component
        Args:
            component (Component): component to remove
        """
        self.page().runJavaScript(
            f"""
            stage.removeComponents({component})
        """
        )

    def set_focus(self, focus: int) -> None:
        """set the focus for the camera true make rotate the protein
        Args:
            focus (int) : value to set setfocus"""
        self.page().runJavaScript(
            f"""
            stage.setFocus({focus})
        """
        )

    def set_impostor(self, bool: bool) -> None:
        """set impostor value for stage

        Args:
            bool (bool):value to set impostor
        """
        bool = self.bool_python_to_js(bool)
        self.page().runJavaScript(
            f"""
            stage.setImpostor({bool})

        """
        )

    def set_parameters(self, params: dict) -> None:
        """set parameters for stage

            Args:
                params (dict):
        ambientColor: string | number
        ambientIntensity: number
        backgroundColor: string | number
        cameraEyeSep: number
        cameraFov: number
        cameraType: "perspective" | "orthographic" | "stereo"
        clipDist: number
        clipFar: number
        clipNear: number
        fogFar: number
        fogNear: number
        hoverTimeout: number
        impostor: boolean
        lightColor: string | number
        lightIntensity: number
        mousePreset: "default" | "pymol" | "coot" | "astexviewer"
        panSpeed: number
        quality: "high" | "medium" | "low" | "auto"
        rotateSpeed: number
        sampleLevel: number
        tooltip: boolean
        workerDefault: boolean
        zoomSpeed: number

        """
        self.page().runJavaScript(
            f"""
        stage.setParameters({params})
        """
        )

    def set_quality(self, quali: str) -> None:
        """set display's quality

        Args:
            quali (str): can take the following value "auto" | "low" | "medium" | "high"
        """
        self.page().runJavaScript(
            f"""
        stage.setQuality({quali})
        """
        )

    def set_size(self, width: str, height: str) -> None:
        """set display's size

        Args:
            width (str): display's width
            height (str): display's height
        """
        self.page().runJavaScript(
            f"""
        stage.setSize({width}, {height})
        """
        )

    def set_rock(self, rock: bool) -> None:
        """set the rock for the camera true make rocking the protein
        Args:
            rock (bool) : value to set setrock"""
        rock = NGLWidget.bool_python_to_js(rock)
        self.page().runJavaScript(
            f"""
            stage.setRock({rock})
        """
        )
        self.rock = True
        if self.spin:
            self.spin = False

    def set_spin(self, spin: bool) -> None:
        """set the spin for the camera true make rotate the protein
        Args:
            spin (bool) : value to set setSpin"""
        spin = NGLWidget.bool_python_to_js(spin)
        self.page().runJavaScript(
            f"""
            stage.setSpin({spin})
        """
        )
        self.spin = True
        if self.rock:
            self.rock = False

    def toggle_full_screen(self, element: str) -> None:
        """toggle the screen

        Args:
            element (str): HTMLElement
        """
        self.page().runJavaScript(
            f"""
        stage.togglFullScreen()
        """
        )

    def toggle_full_screen(self, element: str) -> None:
        """toggle the screen

        Args:
            element (str): HTMLElement
        """
        self.page().runJavaScript(
            f"""
        stage.togglFullScreen({element})
        """
        )

    def toggle_rock(self) -> None:
        """toggle the rock"""
        self.page().runJavaScript(
            """
        stage.toggleRock()
        """
        )

    def toggle_spin(self) -> None:
        """toggle the spin"""
        self.page().runJavaScript(
            """
        stage.toggleSpin()
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

        self.comborepresentation = QComboBox()
        self.comborepresentation.addItems(
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
        self.comborepresentation.currentTextChanged.connect(
            self.update_comborepresentation
        )

        self.combomolcolor = QComboBox()
        self.combomolcolor.addItems(
            ["red", "blue", "green", "pink", "purple", "orange"]
        )
        self.combomolcolor.currentTextChanged.connect(self.update_combomolcolor)

        self.comboAAcolor = QComboBox()
        self.comboAAcolor.addItems(["blue", "red", "green", "pink", "purple", "orange"])
        self.comboAAcolor.currentTextChanged.connect(self.update_comboAAcolor)

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
        cameraaction.triggered.connect(self.view.auto_view)

        self.spin = QCheckBox("spin")
        self.spin.stateChanged.connect(self.view.set_spin)
        self.spin.stateChanged.connect(self.update_controller)

        self.rock = QCheckBox("rock")
        self.rock.stateChanged.connect(self.view.set_rock)
        self.rock.stateChanged.connect(self.update_controller)

        self.textpos = QLabel("position")
        self.selectpos = QLineEdit("1")
        self.selectpos.setFixedSize(80, 15)
        self.selectpos.editingFinished.connect(self.update_position)

        self.selectmol = QLineEdit("1crn")
        self.selectmol.setFixedSize(80, 15)

        self.toolbar2.addWidget(self.comborepresentation)
        self.toolbar2.addWidget(self.combomolcolor)
        self.toolbar2.addWidget(self.comboAAcolor)
        self.toolbar2.addWidget(self.spin)
        self.toolbar2.addWidget(self.rock)
        self.toolbar2.addWidget(self.textpos)
        self.toolbar2.addWidget(self.selectpos)
        self.toolbar2.addWidget(self.selectmol)

    def init(self) -> None:
        """init the value of ngl_Widget"""

        self.view.position = self.selectpos.text()
        self.view.representation = self.comborepresentation.currentText()
        self.view.colormol = self.combomolcolor.currentText()
        self.view.colorAA = self.comboAAcolor.currentText()

    def on_charger(self) -> None:
        """set the correct value and load the molecule"""
        self.view.filename = "rcsb://" + self.selectmol.text()
        if not self.view.mol_loaded:
            self.init()
        if not (self.view.sized):
            self.resize()
        self.view.load_mol()

    def update_comborepresentation(self) -> None:
        """update the spin value and refresh"""
        self.view.representation = self.comborepresentation.currentText()
        if self.view.mol_loaded:
            self.on_charger()

    def update_combomolcolor(self) -> None:
        """update the color value and refresh"""
        self.view.colormol = self.combomolcolor.currentText()
        if self.view.mol_loaded:
            self.on_charger()

    def update_comboAAcolor(self) -> None:
        """update the color value and refresh"""
        self.view.colorAA = self.comboAAcolor.currentText()
        if self.view.mol_loaded:
            self.on_charger()

    def update_position(self) -> None:
        """update selected position
        doc : http://nglviewer.org/ngldev/api/manual/selection-language.html"""
        self.view.position = self.selectpos.text()
        if self.view.mol_loaded:
            self.on_charger()

    def update_protein(self) -> None:
        """update selected protein"""
        self.view.filename = "rcsb://" + self.selectmol.text()
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

    def update_controller(self) -> None:
        """update controller"""
        if not self.view.spin:
            self.spin.setCheckState(Qt.CheckState(0))

        if not self.view.rock:
            self.rock.setCheckState(Qt.CheckState(0))

        print(self.view.spin, self.view.rock)


if __name__ == "__main__":

    app = QApplication(sys.argv)

    w = MainWindow()
    w.show()

    app.exec_()
