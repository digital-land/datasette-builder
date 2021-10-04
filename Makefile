include makerules/makerules.mk

BUILD_TAG_FACT := digitalland/fact_v2
BUILD_TAG_TILE := digitalland/tile_v2
CACHE_DIR := var/cache/
VIEW_MODEL_DB := var/cache/view_model.sqlite3
TILE_DB := var/cache/dataset_tiles.mbtiles
DIGITAL_LAND_DB := var/cache/digital-land.sqlite3
VIEW_CONFIG_DIR := config/view_model/
TILE_CONFIG_DIR := config/tile_server/


DATASETS=\
	$(CACHE_DIR)document-type.sqlite3\
	$(CACHE_DIR)development-plan-type.sqlite3\
	$(CACHE_DIR)development-policy-category.sqlite3\
	$(CACHE_DIR)planning-permission-status.sqlite3\
	$(CACHE_DIR)planning-permission-type.sqlite3\
	$(CACHE_DIR)ownership-status.sqlite3\
	$(CACHE_DIR)site-category.sqlite3\
	\
	$(CACHE_DIR)local-authority-district.sqlite3\
	$(CACHE_DIR)parish.sqlite3\
	\
	$(CACHE_DIR)ancient-woodland.sqlite3\
	$(CACHE_DIR)area-of-outstanding-natural-beauty.sqlite3\
	$(CACHE_DIR)brownfield-land.sqlite3\
	$(CACHE_DIR)brownfield-site.sqlite3\
	$(CACHE_DIR)conservation-area.sqlite3\
	$(CACHE_DIR)development-policy.sqlite3\
	$(CACHE_DIR)development-plan-document.sqlite3\
	$(CACHE_DIR)document.sqlite3\
	$(CACHE_DIR)green-belt.sqlite3\
	$(CACHE_DIR)heritage-coast.sqlite3\
	$(CACHE_DIR)historic-england/battlefield.sqlite3\
	$(CACHE_DIR)historic-england/building-preservation-notice.sqlite3\
	$(CACHE_DIR)historic-england/certificate-of-immunity.sqlite3\
	$(CACHE_DIR)historic-england/heritage-at-risk.sqlite3\
	$(CACHE_DIR)historic-england/listed-building.sqlite3\
	$(CACHE_DIR)historic-england/park-and-garden.sqlite3\
	$(CACHE_DIR)historic-england/protected-wreck-site.sqlite3\
	$(CACHE_DIR)historic-england/scheduled-monument.sqlite3\
	$(CACHE_DIR)historic-england/world-heritage-site.sqlite3\
	$(CACHE_DIR)special-area-of-conservation.sqlite3\
	$(CACHE_DIR)ramsar.sqlite3\
    	$(CACHE_DIR)site-of-special-scientific-interest.sqlite3\
	$(CACHE_DIR)article-4-direction.sqlite3

all:: build

collect: $(CACHE_DIR)organisation.csv $(DATASETS) $(DIGITAL_LAND_DB)
	aws s3 sync s3://digital-land-view-model $(CACHE_DIR) --exclude='*' --include='view_model.sqlite3' --include='*.mbtiles'

build: docker-check $(DIGITAL_LAND_DB)
	datasette_builder build-view-queries $(VIEW_CONFIG_DIR)
	datasette_builder package --data-dir $(CACHE_DIR) --ext "sqlite3" --tag $(BUILD_TAG_FACT) --options "-m $(VIEW_CONFIG_DIR)metadata_generated.json,--install=datasette-leaflet-geojson,--install=datasette-cors"
	datasette_builder package --data-dir $(CACHE_DIR) --ext "mbtiles" --tag $(BUILD_TAG_TILE) --options "-m $(TILE_CONFIG_DIR)metadata.json,--install=datasette-cors,--install=datasette-tiles,--plugins-dir=$(TILE_CONFIG_DIR)plugins/"


push: docker-check
	docker push $(BUILD_TAG_FACT)_digital_land
	docker push $(BUILD_TAG_TILE)_digital_land

test:
	python -m pytest -vvs tests

lint: black-check flake8

black-check:
	black --check  . --exclude '/(src|\.venv/)'

flake8:
	flake8 --exclude 'src,.venv' .

clobber::
	rm $(CACHE_DIR)*

docker-check:
ifeq (, $(shell which docker))
	$(error "No docker in $(PATH), consider doing apt-get install docker OR brew install --cask docker")
endif

$(CACHE_DIR)organisation.csv:
	@mkdir -p $(CACHE_DIR)
	curl -qfsL "$(SOURCE_URL)organisation-dataset/main/collection/organisation.csv" > $(CACHE_DIR)organisation.csv

#  download cached copy of dataset
#
$(CACHE_DIR)%.sqlite3:
	@mkdir -p $(CACHE_DIR)
	curl -qfsL $(call dataset_url,$(basename $(notdir $@)),$(basename $(notdir $@))) > $@

#  the collection should come from the specification ..
$(CACHE_DIR)historic-england/%.sqlite3:
	@mkdir -p $(CACHE_DIR)/historic-england
	curl -qfsL $(call dataset_url,$(basename $(notdir $@)),historic-england) > $@

#  digital-land specification, collections, pipelines, logs, issues, etc
$(DIGITAL_LAND_DB):
	@mkdir -p $(CACHE_DIR)
	curl -qfsL 'https://digital-land-collection.s3.eu-west-2.amazonaws.com/digital-land.sqlite3' > $@

$(VIEW_MODEL_DB):
	@mkdir -p $(CACHE_DIR)
	curl -qfsL 'https://digital-land-view-model.s3.eu-west-2.amazonaws.com/view_model.sqlite3' > $@

$(TILE_DB):
	@mkdir -p $(CACHE_DIR)
	curl -qfsL 'https://digital-land-view-model.s3.eu-west-2.amazonaws.com/dataset_tiles.mbtiles' > $@
