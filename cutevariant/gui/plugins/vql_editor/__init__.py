from PySide2.QtWidgets import QApplication
__title__ = "VQL Editor"
__description__ = "A VQL editor"
__long_description__ = QApplication.instance().translate("vql_editor", """
<p>This plugin allows you to manage most of the work that can be done in a 
Cutevariant project by writing and executing VQL queries.</p>

<p>VQL is a <i>Domain Specific Language</i>, its main purpose is to filter variants
in the same fashion as a SQL query.</p>
<p>The VQL language can be run from the user interface via this plugin or directly
via the command line of Cutevariant.</p>

<p>Although the plugin offers auto-completion (do not forget the joker character '!')
and syntax highlighting, if you want to have more details on how to write your own VQL queries,
as well as the keywords of the language, please see the project wiki page:</p>

<a href="https://github.com/labsquare/cutevariant/wiki/VQL-language">
https://github.com/labsquare/cutevariant/wiki/VQL-language</a>
""")
__author__ = "Sacha schutz"
__version__ = "1.0.0"
