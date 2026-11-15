# Datasette Builder

[![License](https://img.shields.io/github/license/mashape/apistatus.svg)](https://github.com/digital-land/datasette-builder/blob/master/LICENSE)
[![deploy datasette](https://github.com/digital-land/datasette-builder/actions/workflows/deploy.yml/badge.svg)](https://github.com/digital-land/datasette-builder/actions/workflows/deploy.yml)

This repository builds the Docker image that serves the planning data SQLite databases with
[Datasette](https://datasette.io/). In each environment the databases are synced to EFS from the collection S3 bucket
and mounted at `/mnt/datasets`.

It also contains `datasette_builder`, a Datasette plugin installed into the image, which:

* hardens every SQLite connection that serves the public SQL query box: queries may only call plain SQLite's
  functions (every SpatiaLite function is denied), SpatiaLite's virtual tables can't be read, `fts3_tokenizer` is
  blocked, no database can be attached, and value and query sizes are capped. The reasons are documented in
  [hardening.py](src/datasette_builder/hardening.py).
* makes the service read-only over HTTP: anything other than `GET`, `HEAD` and `OPTIONS` is refused with 405, so
  Datasette's state-changing routes (such as the `/-/messages` banner) can't be used, including from another website
  through a visitor's browser. The reasons are documented in [read_only.py](src/datasette_builder/read_only.py).
* replaces Datasette's `escape_css_string` template filter with a strict allowlist, so column names (which come from
  the visitor's SQL on the query page) can't add rules to the page's inline stylesheet. The reasons are documented in
  [css_escaping.py](src/datasette_builder/css_escaping.py).
* overrides the `_table.html` template to link to resources in the digital-land database

SpatiaLite is installed and loaded because the pipeline builds every dataset database with SpatiaLite metadata, which
Datasette can't open without it. Spatial SQL is not available in the query box; geometry is available as text.

The repository follows the [repository structure conventions](https://github.com/digital-land/digital-planning-ways-of-working).

## Layout

```
src/datasette_builder/   the plugin, registered through the `datasette` entry point in pyproject.toml
  templates/             template overrides
docker/startup.sh        container entrypoint: serves every dataset listed in inspect-data-all.json
scripts/                 local-development helpers
tests/datasette_builder/ unit, integration and acceptance tests
requirements/            requirements.txt (deployed, hashed) and dev-requirements.txt, compiled by `make lock`
```

## Development

You need Python 3.13 and Docker.

```
make init          # create .venv and install the dev dependencies, including this project (editable)
make test          # unit, integration and acceptance tests (acceptance needs Docker running)
make docker-test   # the same tests, run inside a container on the image's Python and SQLite
make lint          # ruff, plus the tests/ __init__.py check
make format        # apply ruff formatting and fixes
```

Each test level can also be run on its own with `make unit`, `make integration` or `make acceptance`.

* **unit**: the hardening logic, on plain `sqlite3` connections
* **integration**: the plugin loaded by Datasette in-process
* **acceptance**: the deployable image, started with [testcontainers](https://testcontainers.com/) and fixture
  datasets, checked over HTTP as a visitor would use it

`make docker-test` is useful when something passes or fails locally for reasons specific to your machine. It mounts
the Docker socket into the test container so the acceptance tests can start the image.

The SpatiaLite integration tests need SpatiaLite, set with `SQLITE_EXTENSIONS=mod_spatialite`. Without it (the usual
case on a laptop) `make test` skips them with a message; they always run in `make docker-test` and in CI, and the
acceptance tests cover SpatiaLite through the image either way.

### Dependencies

Runtime dependencies are declared in `pyproject.toml`; dev tools in `requirements/dev-requirements.in`. After changing
either, run `make lock` (or `make lock UPGRADE=1` to upgrade every pin) and commit the regenerated
`requirements/*.txt` files.

### Running the service locally

You need AWS credentials (the preference is [aws-vault](https://github.com/99designs/aws-vault)), the AWS CLI and jq,
plus the name of an S3 bucket that holds the SQLite files. The first run downloads them into `./files`:

`aws-vault exec dl-prod -- make dev BUCKET=<environment>-collection-data`

Datasette is then available at http://localhost:5000.

## Deploying

Merging to `main` runs the tests and, if they pass, builds and pushes the image for each environment. Pull requests
run the same tests. Deployments requiring approval can be found
[here](https://github.com/digital-land/datasette-builder/actions).

# Licence

The software in this project is open source and covered by the [LICENSE](LICENSE) file.

Individual datasets copied into this repository may have specific copyright and licensing, otherwise all content and
data in this repository is [© Crown copyright](http://www.nationalarchives.gov.uk/information-management/re-using-public-sector-information/copyright-and-re-use/crown-copyright/)
and available under the terms of the [Open Government 3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/)
licence.
