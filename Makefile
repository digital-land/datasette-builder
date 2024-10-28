.PHONY: init start clean

init::
	pip install --upgrade pip
ifneq (,$(wildcard requirements.txt))
	pip3 install --upgrade -r requirements.txt
endif 


./files:
	@bash download-files.sh $$BUCKET

start: ./files
	docker-compose up

clean:
	@rm -rf ./files
