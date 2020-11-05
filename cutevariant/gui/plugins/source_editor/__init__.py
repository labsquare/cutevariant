from PySide2.QtWidgets import QApplication
__title__ = "Selections"
__description__ = "A plugin to display selections"
__long_description__ = QApplication.instance().translate("source_editor", """
<p>It is a plugin allowing to work on a subset of variants.<br>
A subset of variants is called selection or source.
</p>
<p>Note that the default selection is called <i>"variants"</i> and contains all
the variants of the project without any filtering or processing.
<b>This selection cannot be deleted or renamed.</b>
</p>
Each selection can be submitted to a set operation with respect to another selection.<br>
The following set operations are available via the context menu:

<ul>
<li>Intersection</li>
<li>Difference</li>
<li>Union</li>
</ul>

You can create a selection in several ways:

<ul>
<li>Via this plugin by importing the content of a BED file (Browser Extensible Data),
whose intervals will be used to filter the variants of the starting selection;</li>
<li>Via a Word set, from the <em>WordSet</em> plugin and via the 
<em>Filters Editor</em> plugin;</li>
<li>Via custom filters, from the <em>Filters Editor</em> plugin.</li>
</ul>
""")
__author__ = "Sacha schutz"
__version__ = "1.0.0"
