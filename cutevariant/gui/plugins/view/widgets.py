from cutevariant.gui import plugin


class QueryViewWidget(plugin.PluginWidget):
    def __init__(self, parent = None):
        super().__init__(parent)
        self.widget_location = plugin.CENTRAL_LOCATION 
        self.view = QTreeView()

        main_layout = QVBoxLayout()
        main_layout.addWidget(self.view)

        self.setLayout(main_layout)


