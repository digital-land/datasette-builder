BUILD_TAG := bram2000/data

all: lint test

collect:
	mkdir -p data
	datasette_builder collect ./datasets.csv

build:
	datasette_builder package --tag $(BUILD_TAG) ./datasets.csv

push:
	docker push $(BUILD_TAG)_digital_land

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

clobber:
	rm data/*
