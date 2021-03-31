all: lint test

test:
	python -m pytest -vvs tests

lint: black-check flake8

black-check:
	black --check .

flake8:
	flake8 .

init:
	pip install -e .
	pip install -r requirements.txt
