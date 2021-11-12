FROM python:3.8
RUN mkdir -p app
WORKDIR /app

RUN apt-get update && \
    apt-get install -y python3-dev gcc libsqlite3-mod-spatialite && \
    rm -rf /var/lib/apt/lists/*

ENV SQLITE_EXTENSIONS '/usr/lib/x86_64-linux-gnu/mod_spatialite.so'
RUN pip install -U datasette

RUN pip uninstall -y uvicorn
RUN pip install uvicorn[standard] gunicorn environs
RUN pip install -e git+https://github.com/digital-land/datasette@allow-bidirectional-joins#egg=datasette
RUN pip install csvkit

EXPOSE 5000

ADD app.py .
ADD settings.json .
ADD metadata.json .
ADD fetch_and_run_datasette.sh /usr/local/bin/fetch_and_run_datasette.sh

ENTRYPOINT ["/usr/local/bin/fetch_and_run_datasette.sh"]
