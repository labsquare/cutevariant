from PySide2.QtWidgets import QApplication
__title__ = "Variants"
__description__ = "The default view for variants DB"
__long_description__ = QApplication.instance().translate("variant_view", """
<p>This window is the main window of Cutevariant. Here you will find the variants
and their related data presented in the various columns selected from the
<em>Columns selector</em> plugin.</p>

You can:

<ul>
<li><b>Group the variants</b> according to the columns of your choice.
This function is interesting if you display the data of sometimes numerous
annotations for the same variant.
You will find all the annotations grouped for each variant.</li>

<li><b>Set the ACMG score</b> of a variant in 2 clicks via the context menu.</li>

<li><b>Mark one or more variants as favorite(s)</b> so that you can easily find
them later.</li>

<li>Edit/add comments.</li>

<li><b>Consult external databases</b> referencing each selected variant to
quickly obtain additional information.</li>

<li><b>Copy</b> one or more variants into a format that can be used directly in
a Calc/Excel spreadsheet.</li>
</ul>

<p>The displayed variants can be <b>controlled by filters</b> modified in real
time from the <em>Filters Editor</em> plugin or from a VQL query from the 
<em>VQL Editor</em> plugin.</p>

<p>Each subset of variants thus obtained can be saved as a selection using the
<em>Save variants</em> button.
The selections are listed in the <em>Source Editor</em> plugin.</p>
""")
__author__ = "Sacha schutz"
__version__ = "1.0.0"
