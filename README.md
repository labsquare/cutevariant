# Cutevariant

#Developement in progress
## To test

	git clone git@github.com:labsquare/CuteVariant-python.git
	cd CuteVariant-python
	virtualenv -p /usr/bin/python3 venv
	source ven/bin/activate
	make install_deps
	make run // start application
	make test // start test


## Development & release cycle
Use [zest.releaser](https://zestreleaser.readthedocs.io) to handle the version and distribution through pypi.

    pip install zest.releaser[recommended]

To yield a new release, use:

    fullrelease
