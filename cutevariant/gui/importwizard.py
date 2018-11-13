
from PySide2.QtWidgets import *
from PySide2.QtWidgets import *
import sys
import widgets

from cutevariant.core.importer import ImportTask


class SelectPage(QWizardPage):
	def __init__(self):
		super(SelectPage,self).__init__()
		self.setTitle("Select variant file")
		self.setSubTitle("Could be a vcf file or annotated vcf file")

		# Create layout 
		self.main_layout = QVBoxLayout()
		self.edit = widgets.BrowseFileEdit()
		self.main_layout.addWidget(self.edit)

		self.setLayout(self.main_layout)

		self.registerField("filename", self.edit.edit, "text")





class ImportPage(QWizardPage):
	def __init__(self):
		super(ImportPage,self).__init__()
		self.setTitle("Create database file ")
		self.setSubTitle("Click on Start to Import")
		self.main_layout = QVBoxLayout()
		self.progress_bar = QProgressBar()
		self.import_button = QPushButton("Import")
		self.tabwidget = QTabWidget()
		self.logedit  = QTextEdit()

		self.import_layout = QHBoxLayout()
		self.import_layout.addWidget(self.progress_bar)
		self.import_layout.addWidget(self.import_button)



		self.tabwidget.addTab(self.logedit, "Message" )
		self.logedit.setFrameShape(QFrame.NoFrame)
		self.main_layout.addLayout(self.import_layout)
		self.main_layout.addWidget(self.tabwidget)

		self.setLayout(self.main_layout)

		self.import_button.clicked.connect(self.start_import)


	def initializePage(self):
		''' override method ''' 
		self.filename = self.field("filename")
		self.db_filename = self.filename +".db"
		self.task = ImportTask(self.filename, self.db_filename)



	def start_import(self):
		self.progress_bar.setRange(0,0)
		self.task.run()



class FinalPage(QWizardPage):
	def __init__(self):
		super(FinalPage,self).__init__()
		self.setTitle("Resume")



class ImportWizard(QWizard):
	def __init__(self):
		super(ImportWizard,self).__init__()
		self.addPage(SelectPage())
		self.addPage(ImportPage())
		self.addPage(FinalPage())



app = QApplication(sys.argv)


w = ImportWizard()

w.show()

app.exec()
