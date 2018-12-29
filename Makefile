test:
	python -m pytest tests cutevariant -s -vv --doctest-module --ignore=venv

coverage:
	python -m pytest --cov cutevariant tests

run:
	python __main__.py
