SHELL := bash
.PHONY: init lock image unit integration acceptance test docker-test lint format dev clean

PYTHON ?= python3.13
VENV := .venv
BIN := $(VENV)/bin
IMAGE := datasette-builder:local
TEST_IMAGE := datasette-builder:test
# `make lock UPGRADE=1` upgrades every pin instead of keeping existing ones.
LOCK_ARGS := --allow-unsafe --strip-extras $(if $(UPGRADE),--upgrade)

# Create .venv (if needed) and install the dev lock, including this project (editable).
init:
	test -d $(VENV) || $(PYTHON) -m venv $(VENV)
	$(BIN)/pip install --upgrade pip pip-tools
	$(BIN)/pip-sync requirements/dev-requirements.txt

# Recompile the lock files. Run from the repo root with the image's Python (3.13).
lock:
	$(BIN)/pip-compile $(LOCK_ARGS) --generate-hashes \
		--output-file=requirements/requirements.txt pyproject.toml
	$(BIN)/pip-compile $(LOCK_ARGS) \
		--output-file=requirements/dev-requirements.txt requirements/dev-requirements.in

# The deployable image; the acceptance tests run against it.
image:
	docker build --target runtime -t $(IMAGE) .

unit:
	$(BIN)/pytest tests/*/unit

integration:
	$(BIN)/pytest tests/*/integration

acceptance: image
	DATASETTE_IMAGE=$(IMAGE) $(BIN)/pytest tests/*/acceptance

# Every level: unit, integration and acceptance. Needs Docker for acceptance.
test: image
	DATASETTE_IMAGE=$(IMAGE) $(BIN)/pytest

# The same suite as `make test`, run inside a container on the image's Python
# and SQLite. The Docker socket is mounted so the acceptance tests can start
# the runtime image next to the test container; host.docker.internal lets them
# reach its published port (works on Docker Desktop and Linux).
docker-test: image
	docker build --target test -t $(TEST_IMAGE) .
	docker run --rm \
		-v /var/run/docker.sock:/var/run/docker.sock \
		--add-host=host.docker.internal:host-gateway \
		-e TESTCONTAINERS_HOST_OVERRIDE=host.docker.internal \
		-e DATASETTE_IMAGE=$(IMAGE) \
		$(TEST_IMAGE)

lint:
	$(BIN)/ruff check .
	$(BIN)/ruff format --check .
	@# Every folder under tests/ needs an __init__.py (repository structure conventions).
	@! find tests -type d ! -name __pycache__ ! -exec test -e '{}/__init__.py' ';' -print | grep .

format:
	$(BIN)/ruff format .
	$(BIN)/ruff check --fix .

# Run the service locally against datasets in ./files, downloading them first
# if needed: make dev BUCKET=<environment>-collection-data
dev: files
	docker compose up --build

# A real directory target: only runs when ./files doesn't exist yet.
files:
	@test -n "$(BUCKET)" || { echo "Set BUCKET=<environment>-collection-data"; exit 1; }
	bash scripts/download-files.sh $(BUCKET)

clean:
	rm -rf files
