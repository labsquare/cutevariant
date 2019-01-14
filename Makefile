test:
	python -m pytest tests cutevariant -vv --doctest-module

coverage:
	python -m pytest --cov cutevariant tests

run:
	python __main__.py
