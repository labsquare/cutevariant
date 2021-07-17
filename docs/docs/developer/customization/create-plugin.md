# Create a plugin

## Plugin module
Plugins are the main components of the application.
All elements that you see on the graphical interface are plugins that come with the cutevariant application.     
Plugins are python modules located in the plugins folder. If you want to create your own plugin, you must create a module with the following structure. 
The plugin module contains following files. 


```txt
plugins/
├─ plot_graph/  
   └─ __init__.py  // 1
   └─ widget.py    // 2
   └─ settings.py  // 3
   └─ dialog.py    // 4
   └─ test.py      // 4
```

1. Module description with plugin name, author, version and text description
2. A widget plugin for the main view. Contain a class inherited from **PluginWidget**
3. A settings widget in settings dialog. Contain a class inherited from **PluginSettingDialog**
4. A dialog widget available from tool menu. Contain a class inherited from **PluginDialog**
5. Testing your plugin is strongly advice


## Plugin Dialog
Plugin dialog are available from the main window tool menu. There are intended to perform action independently of the main window.     
To create a plugin dialog, create file dialog.py with a class inherited from PluginDialog. You can interact with the sqlite database using self.conn. 

!!! warning 
	the class name must be the same as the module name. 
	Here, the module name is `plot_graph` in snake case. Then the class must be `PlotGraphDialog` in camel calse.

Here is a short example showing a dialog with a button triggered a print action. 

```python
from cutevariant.gui.plugin import PluginDialog

class PlotGraphDialog(PluginDialog):
    """Model class for all tool menu plugins

    These plugins are based on DialogBox; this means that they could be opened
    from the tools menu.
    """

    def __init__(self, parent: MainWindow =None):
        """
        Keys:
            parent (QMainWindow): cutevariant Mainwindow
        """
        super().__init__(parent)

        self.button = QPushButton("hello", self)
        self.button.clicked.connect(self.on_click)

    def on_click(self):
    	print(" I m using this sqlite connection", self.conn)



```

## Plugin Widget

To create a plugin is displayed in the main window, you have to create a class inherited from PluginWidget in the widget.py. 

!!! warning 
	the class name must be the same as the module name. 
	Here, the module name is `plot_graph` in snake case. Then the class must be `PlotGraphPlugin` in camel calse.

Three methods can be overloaded to react from the mainwindow.

```python
from cutevariant.gui.plugin import PluginWidget

class PlotGraphPlugin(PluginWidget):

	# Location of the plugin in the mainwindow
	# Can be : DOCK_LOCATION, CENTRAL_LOCATION, FOOTER_LOCATION
    LOCATION = DOCK_LOCATION
    # Make the plugin enable. Otherwise, it will be not loaded
    ENABLE = TRUE

    # Refresh the plugin only if the following state variable changed.
    # Can be : fields, filters, source 
    REFRESH_STATE_DATA = set("fields","filters")

    def on_register(self, mainwindow: MainWindow):
        """This method is called when the plugin is registered from the mainwindow. 
        
        This is called one time at the application startup.

        Args:
            mainwindow (MainWindow): cutevariant Mainwindow
        """
        pass

    def on_open_project(self, conn: sqlite3.Connection):
        """This method is called when a project is opened
		
		Do your initialization here.
        You may want to store the conn variable to use it later. 
     
        Args:
            conn (sqlite3.connection): A connection to the sqlite project
        """
        pass

    def on_refresh(self):
        """This method is called from mainwindow.refresh_plugins()
		
		You may want to overload this method to update the plugin state 
		when query changed
        """
        pass
```

## Plugin Settings 

Settings widget makes possible to configure your plugin with a user interface. They are available from mainwindow > settings menu. 
To create a settings widget, create a file settings.py with a class inherited from `settings.SectionWidget`. This class contains a list of `AbstractSettingsWidget` displayed as page in settings dialog.


```python

from cutevariant.gui.plugin import PluginSettingsWidget
from cutevariant.gui.settings import AbstractSettingsWidget
from PySide2.QtWidgets import QSpinBox


class SampleMemorySettings(AbstractSettingsWidget):

	def __init__(self, parent = None):
		super().__init__(parent)

		self.input = QSpinBox(self)

	def save(self):
		config = self.create_config()
		config["memory"] = self.input.value()
		config.save() 

	def load(self):
		config = self.create_config()
		self.input.setValue(config.get("memory", 32))


class SamplePluginSettingsWidget(PluginSettingsWidget):
    """Model class for settings plugins"""

    def __init__(self, parent = None):
    	super().__init__()

    	self.add_page(SampleMemorySettings())




```
