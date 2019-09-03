from cutevariant.gui import plugin

from PySide2.QtWidgets import *
import sys
from cutevariant.gui.plugins.infovariant import widget


class InfovariantPlugin(plugin.Plugin):
    Name = "Info"
    Description = "A plugin to display all variant annotations"
    def __init__(self, parent=None):
        super().__init__(parent)

        self.widget = widget.InfoVariantWidget()

    def on_open_project(self, conn):
        """Overload from Plugin
        
        Arguments:
            conn 
        """
        self.widget.conn = conn

    def get_widget(self):
        return self.widget

    def on_variant_clicked(self, variant):
        self.widget.current_variant = variant


if __name__ == "__main__":

    app = QApplication(sys.argv)

    p = InfovariantPlugin()

    w = p.get_widget()

    w.show()

    app.exec_()
