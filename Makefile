include makerules/makerules.mk

BUILD_TAG := digitalland/fact
CACHE_DIR := var/cache/
VIEW_MODEL_DB := var/cache/view_model.sqlite3

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
	$(CACHE_DIR)conservation-area.sqlite3\
	$(CACHE_DIR)development-policy.sqlite3\
	$(CACHE_DIR)development-plan-document.sqlite3\
	$(CACHE_DIR)document.sqlite3\
	$(CACHE_DIR)green-belt.sqlite3\
	$(CACHE_DIR)heritage-coast.sqlite3\
	$(CACHE_DIR)special-area-of-conservation.sqlite3

all:: build

collect: $(CACHE_DIR)organisation.csv $(DATASETS)

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

clobber::
	rm $(CACHE_DIR)*

docker-check:
ifeq (, $(shell which docker))
	$(error "No docker in $(PATH), consider doing apt-get install docker OR brew install --cask docker")
endif

build-view-model: $(VIEW_MODEL_DB)

$(VIEW_MODEL_DB):
	@rm -f $@
	view_builder create $@
	view_builder load_organisations $@
	# this should be in shell or python ..
	for f in $(DATASETS) ; do echo $$f ; view_builder build --allow-broken-relationships $$(basename $$f .sqlite3) $$f $@ ; done


postprocess-view-model:
	docker build -t sqlite3-spatialite -f SqliteDockerfile .
	docker run -t --mount src=$(shell pwd),target=/tmp,type=bind sqlite3-spatialite -init ./post_process.sql -bail -echo  /tmp/$(CACHE_DIR)view_model.sqlite3 .exit

$(CACHE_DIR)organisation.csv:
	@mkdir -p $(CACHE_DIR)
	curl -qfsL "$(SOURCE_URL)organisation-dataset/main/collection/organisation.csv" > $(CACHE_DIR)organisation.csv

#
#  download cached copy of dataset
#
$(CACHE_DIR)%.sqlite3:
	@mkdir -p $(CACHE_DIR)
	curl -qfsL $(call dataset_url,$(basename $(notdir $@)),$(basename $(notdir $@))) > $@

#  the collection should come from the specification ..
$(CACHE_DIR)historic-england/%.sqlite3:
	@mkdir -p $(CACHE_DIR)/historic-england
	curl -qfsL $(call dataset_url,$(basename $(notdir $@)),historic-england) > $@
