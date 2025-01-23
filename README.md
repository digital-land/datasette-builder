# Datasette Builder

[![License](https://img.shields.io/github/license/mashape/apistatus.svg)](https://github.com/digital-land/datasette-builder/blob/master/LICENSE)
[![deploy datasette](https://github.com/digital-land/datasette-builder/actions/workflows/deploy.yml/badge.svg)](https://github.com/digital-land/datasette-builder/actions/workflows/deploy.yml)

This repository contains files to build a docker image that will leverage EFS to access digital-land database files and 
serve them using Datasette.

The sqlite databases are automatically synced to EFS from the collection S3 bucket for the environment. For this reason
the application cannot be run locally.

# Usage

## Deploy changes

To deploy changes, just add and commit any changes and push to GitHub. Any deployments requiring approval can be found 
[here](https://github.com/digital-land/datasette-builder/actions).

## Test changes locally

To test changes locally you will need the following requirements:

* docker
* docker-compose
* jq
* aws cli

You will also need AWS credentials in your environment, the preference is to use 
[aws-vault](https://github.com/99designs/aws-vault) for this.

You will also need the name of an S3 bucket that has the required sqlite files.

`aws-vault exec dl-prod -- make start BUCKET=<environment>-collection-data`

## Smoke tests

To run smoke tests (implemented with AWS Synthetics Canaries) locally using the stubs of the AWS SDK, simply run:

`make test-smoke`

The smoke tests require Chrome browser and the corresponding version of chromedriver CLI to be installed.

# Licence

The software in this project is open source and covered by the [LICENSE](LICENSE) file.

Individual datasets copied into this repository may have specific copyright and licensing, otherwise all content and 
data in this repository is [© Crown copyright](http://www.nationalarchives.gov.uk/information-management/re-using-public-sector-information/copyright-and-re-use/crown-copyright/) 
and available under the terms of the [Open Government 3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/) 
licence.
