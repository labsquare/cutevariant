from PySide2.QtWidgets import QApplication
__title__ = "Filters"
__description__ = "A plugin to display filters"
__long_description__ = QApplication.instance().translate("filters_editor", """
<p>This plugin is used to filter (show/hide) the variants displayed in the main window.</p>

<p>Start by clicking on the <em>"+"</em> button (Add Condition), an example is displayed.</p>

A filter is composed of 2 types of elements:

<ul>
<li><b>Logical/Boolean operators</b> (<em>OR/AND</em>) containing sub-filters.</li>
<li><b>Sub-filters</b> each applying to a field available in Cutevariant.</li>
</ul>

The conditions represent the most important part of a filter, they are composed of
of 3 interactive fields:

<ul>
<li>the <b>field</b> available for filtering on which the filter will be applied;</li>
<li>the <b>comparison operator</b> to keep or exclude variants;</li>
<li>the <b>value</b> of the field that will be compared to the value in the database.</li>
</ul>

<p>It is possible to work with several values with the operators <em>IN/NOT IN</em> by
separating values with commas, or by using wordsets managed with the <em>WordSets plugin</em>.</p>

Example of syntax:

<ul>
<li><em>gene in my_gene1, my_gene2</em>: Only the 'my_gene1' or 'my_gene2' genes</li>
<li><em>gene in WORDSET, my_word_set</em>: All genes contained in the wordset 'my_word_set'</li>
<li><em>gene in WORDSET ['my_word_set']</em>: idem </li>
<li><em>gene LIKE "C%"</em>: All genes whose name begins with 'C'</li>
<li><em>chr in ('10', 'X')</em>: Only chromosomes 10 or X</li>
<li><em>chr not in 10, 11</em>: The chromosomes other than 10 and 11</li>
</ul>

<p>You can delete or save a filter to retrieve it later by clicking on the "save"
or "delete" buttons.</p>

<br><br><br>
Additional information:

<ul>
<li>the result of a filter can be saved as a selection by clicking on the save
button on the main window;</li>
<li>you can temporarily hide an item by clicking on the "eye" icon;</li>
<li>each item can be removed by clicking on the cross button on its right;</li>
<li>you can work with several logical operators to form complex filters;</li>
To do so, simply right-click on the first item of your filter (<em>AND</em>
by default) and select "Add condition";</li>
<li>each subcondition can be dragged and dropped from one logical group to another.</li>
</ul>
""")
__author__ = "Sacha schutz"
__version__ = "1.0.0"
