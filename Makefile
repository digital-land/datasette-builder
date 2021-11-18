include makerules/makerules.mk

BUILD_TAG_FACT := digitalland/fact_v2


all:: build

build: docker-check 
	docker build -t $(BUILD_TAG_FACT)_digital_land .


push: docker-check
	docker push $(BUILD_TAG_FACT)_digital_land


docker-check:
ifeq (, $(shell which docker))
	$(error "No docker in $(PATH), consider doing apt-get install docker OR brew install --cask docker")
endif
