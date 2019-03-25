test:
	python -m pytest tests cutevariant -vv --doctest-module

coverage:
	python -m pytest --cov cutevariant tests

run:
	cutevariant

black:
	black cutevariant


# development & release cycle
fullrelease:
	fullrelease
install_deps:
	python -c "import configparser; c = configparser.ConfigParser(); c.read('setup.cfg'); print(c['options']['install_requires'])" | xargs pip install -U
install:
	@# Replacement for python setup.py develop which doesn't support extra_require keyword.
	@# Install a project in editable mode.
	pip install -e .[dev]
uninstall:
	pip cutevariant uninstall
