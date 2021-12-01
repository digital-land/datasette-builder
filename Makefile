include makerules/makerules.mk

# TODO add this ECR repository to terraform
BUILD_TAG_FACT := d955696714113.dkr.ecr.eu-west-2.amazonaws.com/fact_v2


all:: build

build: docker-check
	docker build -t $(BUILD_TAG_FACT) .


push: docker-check
	docker push $(BUILD_TAG_FACT)


docker-check:
ifeq (, $(shell which docker))
	$(error "No docker in $(PATH), consider doing apt-get install docker OR brew install --cask docker")
endif
