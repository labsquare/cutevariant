test:
	python setup.py test --addopts "tests cutevariant -vv --doctest-module"

coverage:
	python setup.py test --addopts "--cov cutevariant tests"

run:
	cutevariant

black:
	black cutevariant


# development & release cycle
fullrelease:
	fullrelease
install_deps:
	python -c "import configparser; c = configparser.ConfigParser(); c.read('setup.cfg'); print(c['options']['install_requires']); print(c['options.extras_require']['dev'])" | xargs pip install -U
install:
	@# Replacement for python setup.py develop which doesn't support extra_require keyword.
	@# Install a project in editable mode.
	pip install -e .[dev]
uninstall:
	pip cutevariant uninstall

translations:
	@echo "Search all python files..."
	@echo "SOURCES += \\" > cutevariant.pro
	@find ./cutevariant/ -name '*.py' -exec echo {} \\ \; >> cutevariant.pro
	@echo . >> cutevariant.pro
	@echo "TRANSLATIONS = cutevariant/assets/i18n/fr.ts" >> cutevariant.pro
	@#pylupdate4 -noobsolete -verbose cutevariant.pro
	pylupdate4 -verbose cutevariant.pro
	@#pyside2-lupdate -verbose cutevariant.pro
	@echo "\033[33;5mOpen linguist; do not forget to publish your translations before leaving it!\033[0m"
	linguist cutevariant/assets/i18n/fr.ts
	lrelease cutevariant.pro

check_setups:
	pyroma .

check_code:
	prospector cutevariant/
	check-manifest

missing_doc:
	# Remove D213 antagonist of D212
	prospector cutevariant/ | grep "cutevariant/\|Line\|Missing docstring"

build_windows_blob:
	python make_a_blob.py build_exe