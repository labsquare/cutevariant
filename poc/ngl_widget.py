import PySide2
from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWebEngineWidgets import *
import sys
import json


class JSValue(QEventLoop):
    def __init__(self, page: QWebEnginePage, parent=None):
        """init values

        Args:
            page (QWebEnginePage): page to run java script
        """
        super().__init__(parent=parent)
        self.page = page
        self.value = None

    def parse(self, value: str):
        """load a json in a python variable

        Args:
            value (str): [description]
        """
        self.value = json.loads(value)
        self.quit()

    def run(self, expression: str) -> None:
        """get the js value throught a JSON method

        Args:
            expression (str): js value to get in python
        """
        self.page.runJavaScript(f"JSON.stringify({expression})", 0, self.parse)
        self.exec_()


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
        colormol : str color of unselected part of the molecul
        colorAA : str color of selected part of the molecul
        spin : str if "true" rotate the protein
        rock : str if "true" rock the protein
        mol_loaded : bool is there a mol loaded
        sized : bool True if the window has been resized once
        focus_camera : bool True if the view is center on the position
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
        self.focus_camera = False

        # QWebEngineSettings
        self.settings().setAttribute(
            QWebEngineSettings.LocalContentCanAccessRemoteUrls, True
        )
        self.settings().setAttribute(QWebEngineSettings.LocalStorageEnabled, True)
        self.settings().setAttribute(QWebEngineSettings.FullScreenSupportEnabled, True)

        self.setHtml(self.TEMPLATE)

        # load function to initialise NGLWidget
        self.loadFinished.connect(self.load_tools)
        self.loadFinished.connect(self.set_window_size)

        # Parameter for QWebEnginePage()
        self.page().setBackgroundColor(QColor("white"))

    # Function
    def get_js(self, expression: str) -> dict:
        """get js variable in python

        Args:
            expression (str): variable to get

        Returns:
            Object: python variable corresponding to the js variable
        """
        js_value = JSValue(self.page())
        js_value.run(expression)
        return js_value.value

    def load_mol(self) -> None:
        """load molecule"""

        self.page().runJavaScript(
            """

        position_prot = "%s";
        representation_prot = "%s";
        colormol = "%s";
        colorAA = "%s";
        protein = "%s";
        focus_camera = %s;

        function structure_representation(component, position = position_prot, representation = representation_prot) {
            schememol = set_colorscheme(schememol, colormol);
            schemeAA = set_colorscheme(schemeAA, colorAA);
                // bail out if the component does not contain a structure
            if (component.type !== "structure") return;
                create_representation_scheme(component, "1", representation, "*", schememol);
                create_representation_scheme(component, "1", representation, position, schemeAA);
                create_representation_scheme(component, "2", representation, position, test, 0.5);
                if (focus_camera)
                    component.autoView(position, 2000);
            };
            stage.removeAllComponents();
            stage.loadFile(protein, {reorderAtoms : true, dontAutoBond : true}).then(structure_representation);
            """
            % (
                self.position,
                self.representation,
                self.colormol,
                self.colorAA,
                self.filename,
                self.focus_camera,
            )
        )
        self.handle_resize()
        print("molecule load")
        self.mol_loaded = True

    def load_tools(self) -> None:
        """load constant and function for js"""

        self.page().runJavaScript(
            """

        var stage = new NGL.Stage("viewport", {backgroundColor : "black"});
        var schememol = NGL.ColormakerRegistry.addSelectionScheme([
            ["red", "*"]], "colormol");
        var schemeAA = NGL.ColormakerRegistry.addSelectionScheme([
            ["blue", "*"]], "colorAA");
        var test = NGL.ColormakerRegistry.addSelectionScheme([
            ["green", "*"]], "test");

        function set_colorscheme (scheme, color){
            scheme = NGL.ColormakerRegistry.addSelectionScheme([
                [color, "*"]]);
            return scheme
        };

        function create_representation_scheme(component, scale, representation, position, colorScheme, opacity = 1){
            component.addRepresentation(representation, {
                    sele: position,
                    scale : scale,
                    colorScheme : colorScheme,
                    opacity : opacity,
                });
            return component
            }

                var shape = new NGL.Shape( "shape" );
        var sphereBuffer = new NGL.SphereBuffer( {
            position: new Float32Array( [ 0, 0, 0, 4, 0, 0 ] ),
            color: new Float32Array( [ 1, 0, 0, 1, 1, 0 ] ),
            radius: new Float32Array( [ 1, 1.2 ] )
        } );
        shape.addBuffer( sphereBuffer );
        var shapeComp = stage.addComponentFromObject( shape );
        shapeComp.addRepresentation( "buffer" );
        
    
        """
        )
        self.focus_camera = self.bool_python_to_js(self.focus_camera)
        print("loading done")

    def set_position(self, value: int) -> None:
        """set position to the given value
        Args:
            value (int): value to set
        """

        self.position = value

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

    # NGL function for stage variable implemented in python
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

    def get_anything_by_name(self, name: str) -> dict:
        """Returns a Collection with all components that satisfy the name condition

         Args:
            name (str): component to get by name

        Returns:
            dict: Collections of components
        """
        return self.get_js(f"stage.getAnythingByName({name})")

    def get_box(self) -> None:
        """get the box from stage variable"""
        return self.get_js("stage.getBox()")

    def get_center(self) -> None:
        """get the center from stage variable"""
        return self.get_js("stage.getCenter()")

    def get_components_by_name(self, name: str, components: str) -> dict:
        """Returns a ComponentCollection with all components that satisfy the name and componentType condition.

         Args:
            name (str): component to get by name
            components (str) : type of components

        Returns:
            dict: Collections of components
        """
        return self.get_js(f"stage.getComponentsByName({name}, {components})")

    def get_components_by_object(self, name: str, components: str) -> dict:
        """Returns a ComponentCollection with all components that satisfy the name and componentType condition.

         Args:
            name (str): component to get by name
            components (str) : object of components

        Returns:
            dict: Collections of components
        """
        return self.get_js(f"stage.getComponentsByObject({name}, {components})")

    def get_parameters(self) -> dict:
        """get stage parameters

        Returns:
            dict: parameters from stage
        """
        return self.get_js("stage.getParameters()")

    def get_representaion_by_name(self, name: str, components: str) -> dict:
        """Returns a RepresentationCollection with all representations that satisfy the name and componentType condition.

         Args:
            name (str): component to get by name
            components (str) ! type of components

        Returns:
            dict: Collections of components
        """
        return self.get_js(f"stage.getComponentsByName({name}, {components})")

    def get_zoom(self) -> None:
        """get the zoom of stage"""
        return self.get_js("stage.getZoom()")

    def get_zoom_for_box(self) -> None:
        """get the zoom of stage"""
        return self.get_js("stage.getZoomForBox()")

    def handle_resize(self) -> None:
        """Handle any size-changes of the container element"""
        self.page().runJavaScript(
            f"""
            stage.handleResize()"""
        )

    def load_file(self, path: str, params: dict = {}) -> any:
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

    # classmethod
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
        """init MainWindow to use NGLWidget
        view : NGLWidget to display in the main window
        toolbar_actions : action's toolbar not movable
        toolbar_widgets : widget's toolbar movable on left
        combo_representation : QComboBox choose the NGL predifined molecular representations
        combo_molcolor : QComborBorx select the color for unselected part of the molecule
        combo_AAcolor :QComborBorx select the color for unselected part of the molecule
        camera_type : QComboBox to select camera type in stage parameters
        combo_camera : QCombobox to select a focus view or not on selected molecule
        spin : QCheckBox if checked, rotate the molecule
        rock : QCheckBox if checked, rock the molecule
        static : QChecbox if checked stop rotate or rock
        buttongroup : QButtonGroup make spin/rock/static exclusive selection
        button : QPushButton connected to a test function
        but_params : QPushButon if clicked open stage parameter that can be modified
        select_pos : QLineEdit choose the part of the mol to select it can be an int/ an int-int or a type or a property
        select_mol : QLineEdit name of the mol to load
        stage_parameter : QGridLayout layout to display widget
        widget : QWidget that contains stage parameter, shown with but_params clicked
        """
        super().__init__()

        self.view = NGLWidget()
        self.setCentralWidget(self.view)

        # First toolbar for actions
        self.toolbar_actions = self.addToolBar("toolbar_actions")
        self.toolbar_actions.setMovable(False)

        action = self.toolbar_actions.addAction("Load")
        action.triggered.connect(self.on_charger)

        resize_action = self.toolbar_actions.addAction("resize")
        resize_action.triggered.connect(self.resize)

        # Second toolbar for Widgets and selection
        self.toolbar_widgets = self.addToolBar("toolbar_widgets")
        self.toolbar_widgets.setAllowedAreas(Qt.LeftToolBarArea)
        self.toolbar_widgets.setFloatable(False)

        self.combo_representation = QComboBox()
        self.combo_representation.addItems(
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
        self.combo_representation.textActivated.connect(
            self.update_combo_representation
        )

        self.combo_molcolor = QComboBox()
        self.combo_molcolor.addItems(
            ["red", "blue", "green", "pink", "purple", "orange"]
        )
        self.combo_molcolor.textActivated.connect(self.update_combo_molcolor)

        self.combo_AAcolor = QComboBox()
        self.combo_AAcolor.addItems(
            ["blue", "red", "green", "pink", "purple", "orange"]
        )
        self.combo_AAcolor.textActivated.connect(self.update_comboAAcolor)

        self.camera_type = QComboBox()
        self.camera_type.addItems(["perspective", "orthographic", "stereo"])
        self.camera_type.textActivated.connect(self.update_camera_type)

        self.combo_camera = QComboBox()
        self.combo_camera.addItems(["global view", "focus view"])
        self.combo_camera.textActivated.connect(self.update_view)

        self.spin = QCheckBox("spin")
        self.spin.stateChanged.connect(self.view.set_spin)

        self.rock = QCheckBox("rock")
        self.rock.stateChanged.connect(self.view.set_rock)

        self.static = QCheckBox("static")
        self.static.setChecked(True)

        self.buttongroup = QButtonGroup()
        self.buttongroup.addButton(self.spin)
        self.buttongroup.addButton(self.rock)
        self.buttongroup.addButton(self.static)
        self.buttongroup.setExclusive(True)

        self.button = QPushButton("test")
        self.button.clicked.connect(self.test)

        self.but_params = QPushButton("open params")
        self.but_params.clicked.connect(self.open_parameters)

        text_pos = QLabel("position")
        self.select_pos = QLineEdit("1")
        self.select_pos.setFixedSize(80, 15)
        self.select_pos.editingFinished.connect(self.update_position)

        text_mol = QLabel("  mol name")
        self.select_mol = QLineEdit("1crn")
        self.select_mol.setFixedSize(80, 15)

        self.toolbar_widgets.addWidget(self.combo_camera)
        self.toolbar_widgets.addWidget(self.combo_representation)
        self.toolbar_widgets.addWidget(self.combo_molcolor)
        self.toolbar_widgets.addWidget(self.combo_AAcolor)
        self.toolbar_widgets.addWidget(self.camera_type)
        self.toolbar_widgets.addWidget(self.spin)
        self.toolbar_widgets.addWidget(self.rock)
        self.toolbar_widgets.addWidget(self.static)
        self.toolbar_widgets.addWidget(text_pos)
        self.toolbar_widgets.addWidget(self.select_pos)
        self.toolbar_widgets.addWidget(text_mol)
        self.toolbar_widgets.addWidget(self.select_mol)
        self.toolbar_widgets.addWidget(self.button)
        self.toolbar_widgets.addWidget(self.but_params)

        # Widget to display stage parameters
        self.stage_parameters = QGridLayout()
        self.widget = QWidget()
        self.widget.setLayout(self.stage_parameters)
        self.setLayout(self.stage_parameters)

    # init function used to create the QMainWindow
    def init(self) -> None:
        """init the value of ngl_Widget"""

        self.view.position = self.select_pos.text()
        self.view.representation = self.combo_representation.currentText()
        self.view.colormol = self.combo_molcolor.currentText()
        self.view.colorAA = self.combo_AAcolor.currentText()
        self.init_stage_parameter()

    def init_stage_parameter(self) -> None:
        """loads parameters value"""

        self.parameters = {}
        self.parameters_label = []
        self.parameters_line = []
        parameter = self.view.get_parameters()

        for e in parameter:
            label = QLabel(e)
            self.stage_parameters.addWidget(label)
            if type(parameter[e]) == str:
                line = QLineEdit((parameter[e]))
                line.setFixedSize(50, 15)
                line.editingFinished.connect(self.update_stage_parameters)
                self.stage_parameters.addWidget(line)

            else:
                line = QLineEdit((str(parameter[e])))
                line.setFixedSize(50, 15)
                line.editingFinished.connect(self.update_stage_parameters)
                self.stage_parameters.addWidget(line)

            self.parameters[e] = parameter[e]
            self.parameters_label.append(label)
            self.parameters_line.append(line)

    # connected function
    def open_parameters(self):
        """show stage parameter in a new widget"""
        self.widget.show()

    def on_charger(self) -> None:
        """set the correct value and load the molecule"""
        self.view.filename = "rcsb://" + self.select_mol.text()
        if not self.view.mol_loaded:
            self.init()
        if not self.view.sized:
            self.resize()
        self.view.load_mol()

    def update_combo_representation(self) -> None:
        """update the spin value and refresh"""
        self.view.representation = self.combo_representation.currentText()
        if self.view.mol_loaded:
            self.on_charger()

    def update_combo_molcolor(self) -> None:
        """update the color value and refresh"""
        self.view.colormol = self.combo_molcolor.currentText()
        if self.view.mol_loaded:
            self.on_charger()

    def update_comboAAcolor(self) -> None:
        """update the color value and refresh"""
        self.view.colorAA = self.combo_AAcolor.currentText()
        if self.view.mol_loaded:
            self.on_charger()

    def update_view(self) -> None:
        """update the view"""
        if self.combo_camera.currentText() == "global view":
            self.view.focus_camera = False
            self.view.auto_view()
        if self.combo_camera.currentText() == "focus view":
            self.view.focus_camera = True
        self.view.focus_camera = self.view.bool_python_to_js(self.view.focus_camera)
        if self.view.mol_loaded:
            self.on_charger()

    def update_position(self) -> None:
        """update selected position
        doc : http://nglviewer.org/ngldev/api/manual/selection-language.html"""
        self.view.position = self.select_pos.text()
        if self.view.mol_loaded:
            self.on_charger()

    def update_protein(self) -> None:
        """update selected protein"""
        self.view.filename = "rcsb://" + self.select_mol.text()
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

    def update_camera_type(self) -> None:
        """update camera type"""
        self.view.set_parameters({"cameraType": self.camera_type.currentText()})

    def update_stage_parameters(self) -> None:
        for i in range(len(self.parameters_label)):
            self.parameters[self.parameters_label[i].text()] = self.parameters_line[
                i
            ].text()
        self.view.set_parameters(self.parameters)

    def test(self) -> None:
        print(self.view.get_center())
        print(self.view.get_parameters())
        self.view.set_parameters({"cameraType": "perspective"})
        self.view.set_parameters({"cameraType": "orthographic"})
        self.view.set_parameters({"cameraType": "stereo"})


if __name__ == "__main__":

    app = QApplication(sys.argv)

    w = MainWindow()
    w.show()

    app.exec_()
