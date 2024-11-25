.PHONY: init start clean

init::
	pip install --upgrade pip
ifneq (,$(wildcard requirements.txt))
	pip3 install --upgrade -r requirements.txt
endif 


./files:
	@bash bin/download-files.sh $$BUCKET

./localstack/bootstrap/local-collection-data:
	@bash  bin/download-s3-files.sh $$BUCKET

start: ./files ./localstack/bootstrap/local-collection-data
	docker-compose up -d

start-no-cache:
	docker-compose up -d --no-cache

restart:
	docker-compose restart datasette

stop:
	docker-compose down --rmi local
	
clean:
	@rm -rf ./files
