# Datasette Builder

[![License](https://img.shields.io/github/license/mashape/apistatus.svg)](https://github.com/digital-land/datasette-builder/blob/master/LICENSE)
[![Build and deploy datasette](https://github.com/digital-land/datasette-builder/actions/workflows/deploy.yml/badge.svg)](https://github.com/digital-land/datasette-builder/actions/workflows/deploy.yml)

This repository contains files to build/run a docker image that will collect digital-land database files and serve them using Datasette.

The sqlite databases are collected from the digital-land-collection S3 bukcet
in the AWS digital land dev account on startup.

It fetches the digital-land.sqlite3 and entity.sqlite3 databases.

## Github action

There are two github actions in this repo.

  - [Build](/.github/workflows/build.yml) - builds a new docker image on commit to main and pushes it to ECR repository. This action runs on commit to main.
  - [Deploy](/.github/workflows/deploy.yml) - just restarts the digital land datasette service. The service reloads all sqlite dbs from s3 on startup (i.e. refreshes data). This action runs daily.


## Build & Deployment

The application is running in Elasticbeanstalk in the digital land AWS dev account.

1. Application name: datasette-aws-entity-v2

2. Environment: Datasetteawsentityv2-env

The docker image is built and pushed to [ECR](https://d955696714113.dkr.ecr.eu-west-2.amazonaws.com/digital_land_datasette)

The build of the image, push to dockerhub and initial Elasticbeanstalk was most likely
done directly from a developer machine.

The Elascticbeanstalk application uses this run configuration [Dockerrun.aws.json](Dockerrun.aws.json)


# Licence

The software in this project is open source and covered by the [LICENSE](LICENSE) file.

Individual datasets copied into this repository may have specific copyright and licensing, otherwise all content and data in this repository is [© Crown copyright](http://www.nationalarchives.gov.uk/information-management/re-using-public-sector-information/copyright-and-re-use/crown-copyright/) and available under the terms of the [Open Government 3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/) licence.
