.PHONY: init init-dev start clean piptool-compile piptool-upgrade test test-image test-smoke

init: ./files init-dev

init-dev:
	pip install pip-tools
	pip-sync requirements/requirements.txt requirements/dev-requirements.txt

./files:
	@bash download-files.sh $$BUCKET

start: ./files
	docker-compose up

clean:
	@rm -rf ./files

piptool-compile:
	pip-compile --allow-unsafe requirements/requirements.in
	pip-compile --allow-unsafe requirements/dev-requirements.in

piptool-upgrade:
	pip-compile --allow-unsafe --upgrade requirements/requirements.in
	pip-compile --allow-unsafe --upgrade requirements/dev-requirements.in

# Integration tests against the local Python's SQLite (run `make init-dev` first)
test:
	python -m pytest

# Same tests inside the production image, so they exercise Debian's SQLite build
test-image:
	docker build --platform linux/amd64 -t datasette-builder:test .
	docker run --rm --platform linux/amd64 -u root --entrypoint bash \
		-v $(CURDIR):/src:ro -w /src -e PYTHONDONTWRITEBYTECODE=1 \
		datasette-builder:test -c \
		"pip install -q --root-user-action=ignore -r requirements/dev-requirements.txt && python -m pytest -p no:cacheprovider"

test-smoke:
	cd tests/smoke && \
	pip install -r requirements_test.txt && \
	pytest

