============
Installation
============

From PyPi
=========

.. code-block:: bash

    $ pip install cutevariant # install
    $ cutevariant             # run

.. Installation on Windows

    Pyside2 is not currently (2019 May) functional on Cygwin, so Cutevariant will not work on Cygwin.

        Install Python3.6+
        Install like the previous chapter said.
        Add the path of python scripts executables to your PATH variable; Something like:

    C:\Users\<username>\AppData\Roaming\Python\Python37\Scripts\

    Two executables are generated in this directory:

    - cutevariant_win_dbg.exe: Open a console in background to see debugging messages.

    Note: Qt libs seems to have a very high loglevel and such a verbosity could make the program unusable.

    - cutevariant.exe: Standard executable.

===========
Development
===========

To get tests running
====================

.. code-block:: bash

    git clone git@github.com:labsquare/cutevariant.git
    cd cutevariant
    virtualenv -p /usr/bin/python3 venv
    source ven/bin/activate
    make install # install
    make run     # start application
    make test    # start tests


Development & release cycle
===========================

Use zest.releaser to handle the version and distribution through pypi.

.. code-block:: bash

    # Assume installaton of zest.releaser (installed with [dev] optional dependencies)
    pip install zest.releaser[recommended]

To yield a new release, use:

.. code-block:: bash

    fullrelease


.. Development on Windows (good luck)

        Install Python3.6+

        Install git

        Install make (optional)

        pip install wheel git clone https://github.com/ysard/cutevariant.git git fetch git checkout dev # or devel make install # or pip install --user -e .[dev]

    Executable files are located here:

        Executable path: C:\Users<username>\AppData\Roaming\Python\Python37\Scripts\cutevariant.exe

    Build standalone program/archive/blob[add synonyms here] on Windows using cx_freeze

    Strongly discouraged: You will generate an archive of 350Mo just for a program of less than 900Ko (including 550Ko of fonts and icons).

    Install cx_freeze:

    pip install cx_freeze

    Build a blob:

    make build_windows_blob

    Your blob is in ./build/ directory.

Generate the doc
================

.. code-block:: bash

    pip install -e .[doc]
    make doc

HTML pages are in `docs/build/html`.
