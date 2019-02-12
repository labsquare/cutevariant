from PySide2.QtWidgets import *
from PySide2.QtCore import *

import os
import sqlite3
from cutevariant.core.importer import async_import_file


class FilePage(QWizardPage):
	def __init__(self):
		super().__init__()

		self.setTitle("Select a file")
		self.setSubTitle("supported file are vcf and vcf.gz")

		self.text_edit = QLineEdit()
		self.button = QPushButton("Browse")
		v_layout = QHBoxLayout()

		v_layout.addWidget(self.text_edit)
		v_layout.addWidget(self.button)
		self.setLayout(v_layout)

		self.button.clicked.connect(self._browse)

		self.registerField("filename",self.text_edit,"text")


	def _browse(self):
		filename = QFileDialog.getOpenFileName(self,"open file", QDir.homePath(),"VCF file (*.vcf, *.vcf.gz)")
		if filename:
			self.text_edit.setText(filename[0])


class ImportThread(QThread):

	progress_changed = Signal(int,str)

	def __init__(self):
		super().__init__()
		self._stop = False
		self.filename = None



	def run(self):
		'''override ''' 
		self._stop = False

		db_filename = self.filename + ".db"
		if os.path.exists(db_filename):
			os.remove(db_filename)
		self.conn = sqlite3.connect(db_filename)

		for value, message in async_import_file(self.conn, self.filename):
			if self._stop == True:
				break
			self.progress_changed.emit(value, message)


  

	def stop(self):
		self._stop= True
		self.conn.close()




class ImportPage(QWizardPage):
	def __init__(self):
		super().__init__()

		self.setTitle("Import file")
		self.setSubTitle("Press import to create sqlite database")
		self.text_buttons = ["Import", "Stop"]

		self.thread = ImportThread()
		self.progress = QProgressBar()
		self.import_button = QPushButton(self.text_buttons[0])

		v_layout = QHBoxLayout()
		v_layout.addWidget(self.progress)
		v_layout.addWidget(self.import_button)

		m_layout = QVBoxLayout()

		self.log_edit = QPlainTextEdit()
		self.tab_widget= QTabWidget()
		self.tab_widget.addTab(self.log_edit, "log")
		
		m_layout.addLayout(v_layout)
		m_layout.addWidget(self.tab_widget)
		self.setLayout(m_layout)

		self.log_edit.appendPlainText(self.field("filename"))

		self.thread.started.connect(lambda: self.log_edit.appendPlainText("Started"))
		self.thread.finished.connect(lambda: self.log_edit.appendPlainText("Done"))
		self.import_button.clicked.connect(self.run)
		
		self.thread.progress_changed.connect(self.progress_changed) 



	def progress_changed(self,value, message):
		self.progress.setValue(value)
		self.log_edit.appendPlainText(message)

	def run(self):
		if self.thread.isRunning():
			print("stop thread")
			self.import_button.setDisabled(True)
			self.thread.stop()
			self.import_button.setDisabled(False)
			self.import_button.setText(self.text_buttons[0])
			return 

		else:
			self.thread.filename = self.field("filename")
			self.log_edit.appendPlainText("Import " + self.thread.filename)
			self.import_button.setText(self.text_buttons[1])
			self.thread.start()



class ProjetWizard(QWizard):
	def __init__(self):
		super().__init__()

		self.addPage(FilePage())
		self.addPage(ImportPage())


