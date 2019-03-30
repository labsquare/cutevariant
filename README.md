# Cutevariant

cutevariant is a light standalone viewer of genetic variation written in Python for Qt. It allows you to view and filter VCF and other format files.

![Cutevariant example](https://raw.githubusercontent.com/labsquare/CuteVariant-cpp/master/screencast.gif)

# Installation

    pip install cutevariant # install
    cutevariant             # run


## Developement in progress
Complete rewrite from Cpp to Python 

###  To get tests running

	git clone git@github.com:labsquare/cutevariant.git
	cd cutevariant
	virtualenv -p /usr/bin/python3 venv
	source ven/bin/activate
	make install_deps # install
	make run     # start application
	make test    # start tests


### Development & release cycle

Use [zest.releaser](https://zestreleaser.readthedocs.io) to handle the version and distribution through pypi.

    pip install zest.releaser[recommended]

To yield a new release, use:

    fullrelease
