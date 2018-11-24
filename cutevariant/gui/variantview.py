from PySide2.QtWidgets import * 
from PySide2.QtCore import * 
from PySide2.QtGui import *
from cutevariant.core.model import * 



class VariantDelegate(QItemDelegate):

    def __init__(self, parent = None):
        super(VariantDelegate,self).__init__()

    def sizeHint(self,option,index):
        print("size hint")
        return  QSize(0,30)





class VariantModel(QStandardItemModel):
    def __init__(self, parent=None):
        super(VariantModel,self).__init__()

    def load(self):
        self.clear()

        labels = []
        for field in Field.select():
            labels.append(field.name)

        self.setColumnCount(len(labels))
        self.setHorizontalHeaderLabels(labels)

        count = 0
        for variant in Variant.select():
            items = []
            for key in labels:
                item = QStandardItem(variant[key])
                items.append(item)

            self.appendRow(items)

            count+= 1 

            if count > 100:
                return




class VariantView(QWidget):
    def __init__(self, parent = None):
        super(VariantView,self).__init__()

        self.model = VariantModel()
        self.delegate = VariantDelegate()

        
        self.topbar = QToolBar()
        self.bottombar = QToolBar()
        self.view = QTreeView()

        self.view.setFrameStyle(QFrame.NoFrame)
        self.view.setModel(self.model)
        self.view.setItemDelegate(self.delegate)

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






if __name__ == "__main__":

    app= QApplication()
    v = VariantView()
    v.show()
    app.exec_()