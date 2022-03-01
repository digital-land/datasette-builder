include makerules/makerules.mk

# TODO add this ECR repository to terraform
BUILD_REPO := 955696714113.dkr.ecr.eu-west-2.amazonaws.com
BUILD_TAG_FACT := $(BUILD_REPO)/digital_land_datasette

ifeq ($(AWS_ACCESS_KEY_ID),)
    $(error AWS_ACCESS_KEY_ID must be defined in the environment)
endif
ifeq ($(AWS_SECRET_ACCESS_KEY),)
    $(error AWS_SECRET_ACCESS_KEY must be defined in the environment)
endif
ifeq ($(AWS_DEFAULT_REGION),)
    $(error AWS_DEFAULT_REGION must be defined in the environment)
endif

all:: build

build: docker-check
	docker build -t $(BUILD_TAG_FACT) \
		--build-arg COLLECTION_DATASET_BUCKET_NAME=$(COLLECTION_DATASET_BUCKET_NAME) \
		--build-arg AWS_ACCESS_KEY_ID=$(AWS_ACCESS_KEY_ID) \
		--build-arg AWS_SECRET_ACCESS_KEY=$(AWS_SECRET_ACCESS_KEY) \
		--build-arg AWS_DEFAULT_REGION=$(AWS_DEFAULT_REGION) \
		.

login-docker:
	aws ecr get-login-password --region eu-west-2 | docker login --username AWS --password-stdin $(BUILD_REPO)

push: docker-check login-docker
	docker push $(BUILD_TAG_FACT)
	aws ecs update-service --force-new-deployment --service development-datasette-service --cluster development-datasette-cluster
	aws ecs update-service --force-new-deployment --service staging-datasette-service --cluster staging-datasette-cluster
	aws ecs update-service --force-new-deployment --service production-datasette-service --cluster production-datasette-cluster

docker-check:
ifeq (, $(shell which docker))
	$(error "No docker in $(PATH), consider doing apt-get install docker OR brew install --cask docker")
endif
