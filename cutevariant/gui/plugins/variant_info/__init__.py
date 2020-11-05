from PySide2.QtWidgets import QApplication
__title__ = "InfoVariant"
__description__ = "A plugin to display variant info"
__long_description__ = QApplication.instance().translate("variant_info", """
<p>This plugin allows you to view all the data attached to the currently selected
variant in the main Variant view window.
</p>
<p>Where the main window and the fields editor selector apply to the variants as
a whole, this plugin targets only one variant.
</p>
<p>You will find the data of transcripts, samples, genotypes as well as manually
written comments added by right-clicking on the variant in the main window.
</p>
Data is read-only!
""")
__author__ = "Sacha schutz"
__version__ = "1.0.0"
