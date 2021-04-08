BUILD_TAG := bram2000/data

all: lint test

build:
	datasette_builder package --tag $(BUILD_TAG) ./datasets.csv

push:
	docker push $(BUILD_TAG)

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
