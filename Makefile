BUILD_TAG := digitalland/fact
CACHE_DIR := var/cache/
VIEW_MODEL_DB := data/view_model.sqlite3

all: lint test

collect:
	mkdir -p data
	datasette_builder collect ./datasets.csv

build: docker-check
	datasette_builder build-queries ./metadata.json
	datasette_builder package --tag $(BUILD_TAG) --metadata metadata_generated.json

push: docker-check
	docker push $(BUILD_TAG)_digital_land

test:
	python -m pytest -vvs tests

lint: black-check flake8

black-check:
	black --check  . --exclude '/(src|\.venv/)'

flake8:
	flake8 --exclude 'src,.venv' .

init:
	pip install -e .
	pip install -r requirements.txt

clobber:
	rm data/*

docker-check:
ifeq (, $(shell which docker))
	$(error "No docker in $(PATH), consider doing apt-get install docker OR brew install --cask docker")
endif

$(VIEW_MODEL_DB):
	view_builder create $(VIEW_MODEL_DB)

build-view-model: $(CACHE_DIR)organisation.csv $(VIEW_MODEL_DB)
	view_builder load_organisations $(VIEW_MODEL_DB)
	view_builder build local-authority-district ../datasette-builder/data/local-authority-district.sqlite3 $(VIEW_MODEL_DB)
	view_builder build conservation-area ../datasette-builder/data/conservation-area.sqlite3 $(VIEW_MODEL_DB)
	view_builder build ancient-woodland data/ancient-woodland.sqlite3 $(VIEW_MODEL_DB)
	view_builder build area-of-outstanding-natural-beauty data/area-of-outstanding-natural-beauty.sqlite3 $(VIEW_MODEL_DB)
	view_builder build heritage-coast data/heritage-coast.sqlite3 $(VIEW_MODEL_DB)
	view_builder build development-policy-category ../datasette-builder/data/development-policy-category.sqlite3 $(VIEW_MODEL_DB)
	view_builder build development-plan-type ../datasette-builder/data/development-plan-type.sqlite3 $(VIEW_MODEL_DB)
	view_builder build ownership-status ../datasette-builder/data/ownership-status.sqlite3 $(VIEW_MODEL_DB)
	view_builder build planning-permission-status ../datasette-builder/data/planning-permission-status.sqlite3 $(VIEW_MODEL_DB)
	view_builder build planning-permission-type ../datasette-builder/data/planning-permission-type.sqlite3 $(VIEW_MODEL_DB)
	view_builder build site-category ../datasette-builder/data/site-category.sqlite3 $(VIEW_MODEL_DB)
	view_builder build document-type ../datasette-builder/data/document-type.sqlite3 $(VIEW_MODEL_DB)
	view_builder build --allow-broken-relationships development-policy ../datasette-builder/data/development-policy.sqlite3 $(VIEW_MODEL_DB)
	view_builder build --allow-broken-relationships development-plan-document ../datasette-builder/data/development-plan-document.sqlite3 $(VIEW_MODEL_DB)
	view_builder build --allow-broken-relationships document ../datasette-builder/data/document.sqlite3 $(VIEW_MODEL_DB)
	view_builder build --allow-broken-relationships brownfield-land ../datasette-builder/data/brownfield-land.sqlite3 $(VIEW_MODEL_DB)
	# view_builder index $(VIEW_MODEL_DB)

postprocess-view-model:
	docker build -t sqlite3-spatialite -f SqliteDockerfile .
	docker run -t --mount src=$(shell pwd),target=/tmp,type=bind sqlite3-spatialite -init ./post_process.sql -bail -echo  /tmp/data/view_model.sqlite3 .exit

$(CACHE_DIR)organisation.csv:
	mkdir -p $(CACHE_DIR)
	curl -qs "https://raw.githubusercontent.com/digital-land/organisation-dataset/main/collection/organisation.csv" > $(CACHE_DIR)organisation.csv

