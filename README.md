# Cutevariant

cutevariant is a light standalone viewer of genetic variation written in Python for Qt. It allows you to view and filter VCF and other format files.

![Cutevariant example](https://raw.githubusercontent.com/labsquare/CuteVariant-cpp/master/screencast.gif)

# Installation

    pip install cutevariant # install
    cutevariant             # run
.

# To get tests running

    git clone git@github.com:labsquare/cutevariant.git
    cd cutevariant
    virtualenv -p /usr/bin/python3 venv
    source venv/bin/activate
    make install_deps # install
    make install # pip install -e . 
    make run     # start application
    make test    # start tests
