==================================
Programming chart & code standards
==================================

Introduction
============

To make it a little not-so-harsh for those that actually do understand what are development standards and rules:
Your feedback is important to us, and we appreciate the testing and information that you assist us with.

Why do we need coding standards?
--------------------------------

The point of having style guidelines is to have a common vocabulary of coding so people can concentrate
on what you’re saying rather than on how you’re saying it.

It makes easier to maintain and read all the scripts related code and gives us more control over the code.

In some cases it will be a safe guard against errors.


Why is it important for developers/contributors?
------------------------------------------------

Make your life and that of maintainers easier!
Check everything you do!


Coding Standards
================

Most of these rules are not specific to the project but to the language itself.
However, how to structure a functional code is up to you.

Style errors can be corrected or detected by linters or correctors such as
pylint/prospector and black (see below).


Tabs
----

Python code never contain tabs, instead use spaces.
Most sane development-tools have options to replace tabs with 4 spaces.


Whitespaces
-----------

- No trailing spaces at the end of lines
- Do not fill parenthesis with whitespaces

Wrong:

.. code-block:: python

    if( attack )
    if ( attack )

Correct:

.. code-block:: python

    if (attack)


Comments: where
---------------

Always comment code where it is not typical code repeated in many/all scripts
and/or not self-explanatory what the code does.

Localization of comments:

- Above the line
- At code line (2 spaces after)
- In docstring for important notes

Wrong useless comment:

.. code-block:: python

    # if something equals MY_CONSTANT
    if (something == MY_CONSTANT)


Error handling
--------------

Do not reinvent the wheel.

Use a logger with the available logging levels:

.. code-block:: python

    from cutevariant.commons import logger

    LOGGER = logger()

    LOGGER.debug("My debug string %s", value)  # %s as a placeholder for lazy loading
    LOGGER.info(...)
    LOGGER.warning(...)
    LOGGER.error(...)
    LOGGER.exception(...)

Note: Use lazy loading with placeholders in your debugging texts.
Values passed as arguments will not be casted into strings if the chosen logging level does not require it.


Don't hide stacktraces! It is better not to handle exceptions than to handle them in a way that will prevent debugging.

What do you prefer ?

.. code-block:: python

    ERROR: [mainwindow.py:209:refresh_plugins()] <widgets.FiltersEditorWidget object at 0x7f3cdcf0e348>:205 string indices must be integers

Or:

.. code-block:: python

    Traceback (most recent call last):
        File "/media/DATA/Projets/cutevariant/cutevariant/cutevariant/gui/plugins/auragen_filter/widgets.py", line 75, in on_changed
            self.mainwindow.refresh_plugins(sender=self)
        File "/media/DATA/Projets/cutevariant/cutevariant/cutevariant/gui/mainwindow.py", line 205, in refresh_plugins
            plugin_obj.on_refresh()
        File "/media/DATA/Projets/cutevariant/cutevariant/cutevariant/gui/plugins/filters_editor/widgets.py", line 1477, in on_refresh
            self.model.filters = self.mainwindow.state.filters
        File "/media/DATA/Projets/cutevariant/cutevariant/cutevariant/gui/plugins/filters_editor/widgets.py", line 537, in filters
            self.load(filters)
        File "/media/DATA/Projets/cutevariant/cutevariant/cutevariant/gui/plugins/filters_editor/widgets.py", line 734, in load
            self.root_item.append(self.to_item(data))
        File "/media/DATA/Projets/cutevariant/cutevariant/cutevariant/gui/plugins/filters_editor/widgets.py", line 742, in to_item
            [item.append(self.to_item(k)) for k in data[operator]]
        File "/media/DATA/Projets/cutevariant/cutevariant/cutevariant/gui/plugins/filters_editor/widgets.py", line 742, in <listcomp>
            [item.append(self.to_item(k)) for k in data[operator]]
        File "/media/DATA/Projets/cutevariant/cutevariant/cutevariant/gui/plugins/filters_editor/widgets.py", line 745, in to_item
            item = FilterItem((data["field"], data["operator"], data["value"]))
    TypeError: string indices must be integers


Look where the 205 of the first text came from... Is it informative?

Thereby, wrong:

.. code-block:: python

    try:
        plugin_obj.on_refresh()
    except Exception as e:
        print(e)
        LOGGER.error(
            "{}:{} {}".format(
                plugin_obj, format(sys.exc_info()[-1].tb_lineno), e
            )
        )
        raise

Good:

.. code-block:: python

    try:
        plugin_obj.on_refresh()
    except (ValueError, KeyError) as e:  # Specify the types when possible
        LOGGER.exception(e)



Magic numbers vs. constants
---------------------------

Try to put your constants in cutevariant.commons if they can be used by many files of the project.
Having the same constants at multiple places is error prone during maintenance.


Translations
------------

When doing changes to displayed strings in the GUI, please remember to update the translations.


Docstrings et documentation en général: When to put it/What does it contain
---------------------------------------------------------------------------

Autodocumented code is a myth.
A code that is not or badly documented is of no use to anyone.

Docstrings must answer the questions "what, when, who, why".

The docstring for a function or method should summarize its behavior and document its arguments,
returned value(s), side effects, exceptions raised, and restrictions on when and why it can be called
(all if applicable).


A developer **should not and does not want** to have to grep the whole project to guess where and how a function is called, and thus waste his time scrolling up the call stack to know the ins and outs of a piece of code!

As soon as a function is finished and ready to be committed, check the docstring, send your code only once it's done.

In practice, to guide your implementation, you should write the docstring before the code.


Warnings:

- Docstrings not acceptable (taken from real code):

.. code-block:: python

    """This function is cute because"""  # get straight to the point: "Return x/Do y".

    """Similar to xxxx"""  # use standardized reference (see below) """See Also:: :meth:`xxx`"""

    # You are in `cutevariant/core/writer` directory and read:
    """Expose of high-level reader classes"""


- WTF (real) docstrings:

.. code-block:: python

    """As it says"""
    """Self explained"""
    """it is clear"""
    """For tests only"""


- Do not make blind Copy/Paste that may insert wrong information or that have nothing
  to do with the functions you are writing docstrings for.

- The docstring is a phrase ending with a period. It prescribes the function or method's effect as a command
  ("Do this", "Return that"), not as a description; e.g. don't write "Returns the pathname ...".


Rédaction des docstrings
========================

Python: Docstring Conventions
https://www.python.org/dev/peps/pep-0257
https://www.python.org/dev/peps/pep-0287


Writing is based on standards, in Cutevariant you can find 2 standards:
ReStructuredText (original and historically recommended for Python), Google Napoleon (new one used for x reasons... especially the annotations (typing hints)).

You will find their respective documentations at the end of this chapter.

If you see the first one, keep using it or rewrite everything in the second standard; DO NOT MIX the two!

Note:

    One-line docstrings are accepted for "really obvious cases".
    But make no mistake, the return type is not always so obvious that it doesn't require explanation.


    Example of good candidate for one-line docstring:

        get_value()


reStructuredText (PEP 287):
---------------------------

.. code-block:: python

    """Summary line.

    Extended description of function.

    :meth:`other_function`

    :example:

    coucou

    .. note:: blabla
    .. warning::

    :param int arg1: Description of arg1.
    :param str arg2: Description of arg2.
    :raise: ValueError if arg1 is equal to arg2
    :return: Description of return value
    :rtype: bool

    :example:

    >>> a=1
    >>> b=2
    >>> func(a,b)
    True
    """


Google Napoléon (PEP 484):
--------------------------

Type annotations depend on the typing module used to annotate function signatures:

- https://docs.python.org/3/library/typing.html#typing.List
- https://mypy.readthedocs.io/en/latest/builtin_types.html#built-in-types

.. code-block:: text

    Type                Description
    ----                -----------

    int                 integer of arbitrary size
    float               floating point number
    bool                boolean value
    str                 unicode string
    bytes               8-bit string
    object              an arbitrary object (object is the common base class)
    List[str]           list of str objects
    Dict[str, int]      dictionary from str keys to int values
    Iterable[int]       iterable object containing ints
    Sequence[bool]      sequence of booleans
    Any                 dynamically typed value with an arbitrary type


Typing hints may seem to overload function signatures, **however the description
of argument and return types is absolutely necessary**.
They **must be written, checked, and updated** in case of modification of any function!


Full example:

.. code-block:: python

    from typing import Union, Text

    def fetch_bigtable_rows(big_table, keys, other_silly_variable: Union[None, Text, int])): # or var: Optional[Text] = None
        """Fetches rows from a Bigtable.

        Retrieves rows pertaining to the given keys from the Table instance
        represented by big_table.  Silly things may happen if
        other_silly_variable is not None.

        Args:
            big_table: An open Bigtable Table instance.
            keys (List[str]): A sequence of strings representing the key of each table row
                to fetch.
                =>
            other_silly_variable (bool): Another optional variable, that has a much
                longer name than the other args, and which does nothing.

        Kwargs:
            other_silly_variable (Optional[bool]): Current state to be in.
                => boolean or None

        Returns:
            A dict mapping keys to the corresponding table row data
            fetched. Each row is represented as a tuple of strings. For
            example:

            {'Serak': ('Rigel VII', 'Preparer'),
            'Zim': ('Irk', 'Invader'),
            'Lrrr': ('Omicron Persei 8', 'Emperor')}

            If a key from the keys argument is missing from the dictionary,
            then that row was not found in the table.

        Raises:
            IOError: An error occurred accessing the bigtable.Table object.
        """

Links:

- Python guide Google Napoléon/Sphinx
  https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings


- Official ReSt doc from sphinx
  http://www.sphinx-doc.org/en/1.6/domains.html#cross-referencing-python-objects

- ReStructuredText/Google-style/Numpy-stylem/Doctests
  https://thomas-cokelaer.info/tutorials/sphinx/docstring_python.html
  http://queirozf.com/entries/python-docstrings-reference-examples
  https://stackoverflow.com/questions/3898572/what-is-the-standard-python-docstring-format


Naming of variables, classes, functions and methods
---------------------------------------------------

Syntaxes allowed/recommended in Python:

- snake_case for functions and variables
- CamelCase for classes

Additional rules:

- A function name should be something sweet, short and meaningful about what the function does.
- Remember to use the plural form when designating structures with multiple items.
- Be explicit but not too much. Do not put sentences in your variables!
- Do not use variable with less than 3 letters; EVEN in comprehension loops.
- Do not reuse variables for different purposes than the original one.
- Be consistent: a variable named `map_x` should not be found elsewhere with the name `x_map`.

Wrong:

.. code-block:: python

    test = None
    items = 0
    this_variable_is_a_list_of_items = []

Good:

.. code-block:: python

    my_variable = 0
    variables = []
    variables_mapping = {}


Example:

.. code-block:: python

    class MyClass:
        """DO NOT inherit of <object>, it's deprecated for Python 3"""

        def __init__(self):
            # Please do not forget to declare ALL your instance variables in the constructor,
            # AND to document them in its docstring or in the class's one.
            self._my_attr = None

        @property
        def my_attr(self):
            return self._my_attr

        @my_attr.setter
        def my_attr(self, value):
            self._my_attr = value


Classes
-------

About private and protected variables
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Avoid using underscore in front of variables to "make them private" (i.e. `_my_private_var`).
This concept does not exist much in Python and is not recommended.
However, it is necessary when using properties.


Reserve the use of double underscores/dunders in front of names to rare cases.
While they enable name mangling by the interpreter you may think you are hiding methods/variables
outside of your classes but in reality you are making your code base highly and unnecessarily complex.
Ex: (i.e. `__my_very_very_private_var`)

About properties
~~~~~~~~~~~~~~~~

TL;DR: Properties ARE suitable in Python POO paradigm.

Advantages:

- Standard attribute access is the normal, Pythonic way of, well, accessing attributes.
- Using dedicated getters and setters does not produce Pythonic code.
- Avoids polluting the global space with 3 elements (1 getter, 1 setter, the attribute)
  by replacing them by only 1.
- It makes inheriting accessors from properties cleaner and more straightforward
- Data validation
- Data operation (encapsulation) sans exposition des API non pertinentes
- Stabilization of the API by invisibly replacing simple attribute accesses with controlled accesses.
- Access logging: Allows a debugging mode using a class with properties,
  vs. a class used in production that does not have properties.

Disadvantages:

- Hide expensive treatments from the user who thinks he is simply accessing attributes.


Règles de bonnes pratiques à propos de git
==========================================

Usage
-----

Git commands can take a long time to type in, which in combination with their frequency of use
is a brake on the adoption of complex but indispensable controls.

- use the `~/.git/config` file and fill it with aliases that you will easily remember!
- use your shell and its aliases and functions: don't enter `git` anymore, enter `g` !

Example of aliases you can't do without:

.. code-block:: text

    [alias]
        st = status
        cim = commit -m
        cia = commit --amend
        df = diff
        pa = add --patch
        ss = stash
        sa = stash apply
        sp = stash pop
        sl = stash list

Commits
-------

git is not a way to save your work of several hours or even a day to a dropbox-like storage device.

- Name the commits in a short way;
- Tell **why you do things, not how you do them**.
- Don't mix code for multiple features, files, and so on in a single commit.
- Reserve typographical changes due to linters to a single commit (e.g. "Fix typos").
- Be careful what you add in a commit.

Use `git add --patch`.

git add should NEVER be used except to track NEW files.


Examples of (real) bad commit names:

.. code-block:: text

    Last commit before foing to bed
    before the last
    dont stress
    correction
    matin
    repas

Do not do this!

Push force
----------

TL;DR: Prohibited except on your branches or if your colleagues are sleeping.


- prevents the people we work with from being able to rely on our branch
  because they will have to redo all their work from the rebase

- prevents you from working with people; the commits they propose
  can no longer be merged successively since the history changes with each merge.

- this is tolerated on its own branches, from which nobody works.
  Repository/project managers must not do this on public branches under any circumstances.


https://web.archive.org/web/20090224195437/http://kerneltrap.org/Linux/Git_Management (Torvalds)


Branches
--------

- the master branch is the public stable branch,
- the devel branch should be considered unstable but functional,
- the devel code must be easily transferable to the master.
- the most recent and untested implementations must remain on their respective branches.

Thus, work on a separate branch per feature or patch;
Merge with your devel branch when you consider the work done,
then submit a request for merge by pull-request.


Pull-request & Merging of branches
----------------------------------

- Rather than merging your branch with the common branches yourself,
  If possible, make a pull-request to facilitate the review process.
- A pull-request should not require any modifications (much less purely typographical).
  It is finished code. If possible tested and free of bugs as much as possible.


Highly unpleasant findings that you want to avoid:
Bring the changes of a branch and notice multiple regressions at best,
in the worst case the software doesn't work anymore. This even on the development branch.

Solution:
Do not merge your branches with the branches your co-workers are working on.
Especially if your task is not considered finished and the software is not in a usable state.
Make pull-requests.


When can a work be shared?

- One branch per new feature or patch; that's the rule.

- Follow the typographical and documentation conventions of the project:

    - systematic and mandatory documentation of each function, module, class, etc. via docstrings.
      no code should be pushed without documentation.
    - update the documentation in accordance with the code changes.
    - Import cleanup: it takes 1 second
    - Run the linters regularly (see next chapter).

- Unit tests are ok (see the chapter below)

- Put yourself in the position of someone who discovers your code.


Linters
-------

The linters are configured to monitor critical points to be corrected before pull-request.


- Run them regularly, at the end of the day, at the end of the implementation of a feature.
- Don't blindly follow the changes made; some are quite disgraceful,
  especially for lines exceeding the 80 character limit by a few characters.


Typos modifications must be combined in a commit (a commit name such as "Fix typos" is sufficient)
and not scattered here and there through the commits.

You save yourself work and simplify the review of the commits.


In general you'd better run the black and pylint linters punctually
and learn how to correct yourself than to read all the rules at once.


Reference: Python style guide Google/Sphinx:
https://google.github.io/styleguide/pyguide.html


Best practice rules about feature implementation
================================================

Do not publish on the common branch of the obviously non-functional code.

Example:

    An interface but nothing functional behind it.

    A fake documentation::
    
        # Overview

        Cutevariant is awesome

        ```eval_rst
        .. important:: Doc is not complete
        ```


You have the right to start development with the interface but until it is not fully functional,
do not publish on the branches of your colleagues; at least without notifying them via an issue
or a pull-request..


Unit tests
==========

NEVER disable a broken test or feature to hide a problem!

Loss of test, test simplification or loss of functionality = crap work.


Tests are made to be broken! They break for 2 reasons:

- your code is incorrect and not conform with what is expected
- you have corrected a behaviour that is now the expected behaviour

The first case implies that you correct your code, the second that you correct the test.

To do this, you must:

- Execute the tests and make sure they are compliant before a push.
  on the development branch (devel)
- Write tests for each new feature/function (at least the important ones) written
- Document and maintain documentation of your tests to allow others to to correct their own errors or the test itself.


2 cases can justify not passing the tests for a pull-request:

- mention the problem in the pull-request by asking for advice or help;
- the broken test concerns code not related to the proposed implementation.

