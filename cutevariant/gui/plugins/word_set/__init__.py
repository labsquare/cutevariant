from PySide2.QtWidgets import QApplication
__title__ = "WordSets"
__description__ = "A plugin to manage word sets"
__long_description__ = QApplication.instance().translate("word_sets", """
<p>This plugin allows to create sets of words that can be matched with the
attributes of the project's variants.</p>
<p>
Once the addition of a word set is started, a manual addition one by one of the
words is possible; for practical reasons it is however advisable to directly
import a text file containing merely 1 word per line.</p>

The set can be reworked at any time via an editor.<br>
<br>
<i>Example of use:</i><br>
<br>
<i>A user wishes to quickly filter all variants of a project related to a set of
relevant genes for him.
He therefore creates a word set and then makes a selection via:</i>

<ul>
<li>the <em>Filters Editor</em> plugin with a filter of the type:
<pre>gene IN ('WORDSET', 'my_word_set')</pre></li>

<li>the <em>VQL Editor</em> plugin with a VQL request of the type:
<pre>SELECT chr,pos,ref,alt,gene FROM variants WHERE gene IN WORDSET['my_word_set']</pre></li>
</ul>
""")
__author__ = "Sacha schutz"
__version__ = "1.0.0"
