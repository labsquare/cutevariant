# Qt imports
from PySide2.QtWidgets import QWidget
from PySide2.QtCore import Signal

# Custom imports
from cutevariant.core import Query


class PluginWidget(QWidget):
    """Handy class for dockable widget """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.query_view = None

    def objectName(self):
        """Override: Return an object name based on windowTitle

        .. note:: Some plugins don't set objectName attribute and so their state
            can't be saved with MainWindow's saveState function.
        """
        return self.windowTitle().lower()

    def on_model_changed(self, model):
        pass 

    def on_variant_clicked(self, variant):
        pass

