from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtSvg import *

from PySide2.QtWebEngineWidgets import *

import sys
import genomeview


class GenomeView(QWebEngineView):

	def __init__(self):
		super().__init__()
		self.dataset_paths = ["/DATA/Bioinfo/projects/iscard/data/muted/delcomplete.bam",
                 "/DATA/Bioinfo/projects/iscard/data/bed/colon.design.bed.gz"]
		self.reference = "ftp://ftp.1000genomes.ebi.ac.uk/vol1/ftp/technical/reference/phase2_reference_assembly_sequence/hs37d5.fa.gz"
		self.hg19 = "/DATA/Bioinfo/data/hg19.fa"

		self.load(QUrl("https://igv.org/web/current/examples/bam.html"))


	def set_variant(self, variant):
		print("genom voew set variant")
		chrom = variant["chr"]
		pos = variant["pos"]
		start = pos - 100
		end = pos + 100

		self.page().runJavaScript(f"igv.browser.search('{chrom}:{start}-{end}')")
		#self.load(QUrl("file:///tmp/test/index.html"))






# print("salut")

# app = QApplication(sys.argv)

# w = QWebEngineView()



# w.show()

# app.exec_()