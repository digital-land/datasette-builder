.PHONY: init start clean

init: ./files

./files:
	@bash download-files.sh $$BUCKET

start: ./files
	docker-compose up

clean:
	@rm -rf ./files
