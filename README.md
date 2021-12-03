# Datasette Builder

[![License](https://img.shields.io/github/license/mashape/apistatus.svg)](https://github.com/digital-land/datasette-builder/blob/master/LICENSE)
[![Restart elasticbeanstalk datasette](https://github.com/digital-land/datasette-builder/actions/workflows/restart.yml/badge.svg)](https://github.com/digital-land/datasette-builder/actions/workflows/restart.yml)

This repository contains files to build/run a docker image that will collect digital-land database files and serve them using Datasette.

The sqlite databases are collected from the digital-land-collection S3 bukcet
in the AWS digital land dev account on startup.

It fetches the digital-land.sqlite3 and entity.sqlite3 databases.

## Github action

The github action is this repository does not rebuild the docker image, but rather updates the elasticbeanstalk
enviroment. By update, in this case unless the docker image has changed in the dockerhub (more on that later) we just mean a restart using existing configuration. However it will reload the sqlite databases from the collection bucket thereby ensuring the data is up to date.

The action runs daily.


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
