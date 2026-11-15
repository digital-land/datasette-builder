# ---------------------------------------------------------------------------
# base: everything the service needs to run. Shared by `test` and `runtime`.
# ---------------------------------------------------------------------------
FROM python:3.13-slim AS base

# jq: startup.sh reads the dataset list from inspect-data-all.json
# libsqlite3-mod-spatialite: the pipeline builds dataset databases with
#   SpatiaLite metadata (InitSpatialMetadata), which includes virtual tables
#   whose code lives in SpatiaLite. Datasette can't open those databases
#   without it. Its SQL functions are all denied to public queries by the
#   datasette_builder plugin (see src/datasette_builder/hardening.py).
RUN apt-get update && \
    apt-get install -y --no-install-recommends jq libsqlite3-mod-spatialite && \
    rm -rf /var/lib/apt/lists/*

# Datasette loads these extensions on every connection. Named rather than given
# as a path, so the dynamic loader finds it on any architecture.
ENV SQLITE_EXTENSIONS=mod_spatialite

WORKDIR /app

# Third-party dependencies first, hash-checked, so this layer stays cached
# until the lock changes.
COPY requirements/requirements.txt .
RUN pip install --no-cache-dir --require-hashes -r requirements.txt

# Our package: the Datasette plugin and templates, registered through its
# entry point. --no-deps: everything it needs comes from the lock above.
COPY pyproject.toml .
COPY src src
RUN pip install --no-cache-dir --no-deps . && rm -rf src

COPY docker/startup.sh .

RUN groupadd --system appuser && \
    useradd --system --gid appuser --no-create-home appuser

ENV PORT=5000
EXPOSE 5000

# ---------------------------------------------------------------------------
# test: base + dev tools + tests, for running the whole suite in a container
# (`make docker-test`). Never deployed. Runs as root so it can use the Docker
# socket that `make docker-test` mounts for the acceptance tests.
# ---------------------------------------------------------------------------
FROM base AS test

# dev-requirements.txt installs the project editable (-e file:.), so it needs
# the source back.
COPY src src
COPY requirements/dev-requirements.txt .
RUN pip install --no-cache-dir -r dev-requirements.txt

COPY tests tests

CMD ["pytest"]

# ---------------------------------------------------------------------------
# runtime: what gets deployed. Built from base, so no tests or dev tools.
# ---------------------------------------------------------------------------
FROM base AS runtime

USER appuser

ENTRYPOINT ["bash", "startup.sh"]
