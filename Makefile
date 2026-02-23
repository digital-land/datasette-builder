.PHONY: init start clean piptoool-compile piptool-upgrade

init: ./files
	pip install pip-tools
	pip-sync requirements/requirements.txt

./files:
	@bash download-files.sh $$BUCKET

start: ./files
	docker-compose up

clean:
	@rm -rf ./files

piptool-compile:
	pip-compile requirements/requirements.in

piptool-upgrade:
	pip-compile --upgrade requirements/requirements.in

test-smoke:
	cd tests/smoke && \
	pip install -r requirements_test.txt && \
	pytest

