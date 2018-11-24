from PySide2.QtWidgets import * 
from PySide2.QtCore import * 


class VariantView(QWidget):
    def __init__(self, parent = None):
        super(VariantView,self).__init__()

        self.test = QFileSystemModel()
        self.test.setRootPath("/home/sacha")
        
        self.topbar = QToolBar()
        self.bottombar = QToolBar()
        self.view = QTreeView()

        self.view.setFrameStyle(QFrame.NoFrame)
        self.view.setModel(self.test)

        main_layout = QVBoxLayout()
        main_layout.addWidget(self.topbar)
        main_layout.addWidget(self.view)
        main_layout.addWidget(self.bottombar)
        main_layout.setContentsMargins(0,0,0,0)



        # Construct top bar 
        self.topbar.addAction("test")

        # Construct bottom bar 
        self.page_box = QLineEdit()
        self.page_box.setReadOnly(True)
        self.page_box.setFrame(QFrame.NoFrame)        
        self.page_box.setMaximumWidth(50)
        self.page_box.setAlignment(Qt.AlignHCenter)
        self.page_box.setStyleSheet("QWidget{background-color: transparent;}")
        self.page_box.setText("43")
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.bottombar.addWidget(spacer)
        self.bottombar.addAction("<")
        self.bottombar.addWidget(self.page_box)
        self.bottombar.addAction(">")

        self.bottombar.setContentsMargins(0,0,0,0)




        self.setLayout(main_layout)









app= QApplication()
v = VariantView()
v.show()
app.exec_()