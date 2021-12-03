include makerules/makerules.mk

# TODO add this ECR repository to terraform
BUILD_TAG_FACT := d955696714113.dkr.ecr.eu-west-2.amazonaws.com/digital_land_datasette


all:: build

build: docker-check
	docker build -t $(BUILD_TAG_FACT) .

login-docker:
	aws ecr get-login-password --region eu-west-2 | docker login --username AWS --password-stdin 955696714113.dkr.ecr.eu-west-2.amazonaws.com

push: docker-check login-docker
	docker push $(BUILD_TAG_FACT)
	aws elasticbeanstalk update-environment --application-name datasette-aws-entity-v2 --environment-name Datasetteawsentityv2-env --version-label datasette-entity-v2-source-2

docker-check:
ifeq (, $(shell which docker))
	$(error "No docker in $(PATH), consider doing apt-get install docker OR brew install --cask docker")
endif
