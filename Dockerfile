FROM python:3.8
RUN mkdir -p app
WORKDIR /app

RUN apt-get update && \
    apt-get install -y python3-dev gcc libsqlite3-mod-spatialite && \
    rm -rf /var/lib/apt/lists/*

ENV SQLITE_EXTENSIONS '/usr/lib/x86_64-linux-gnu/mod_spatialite.so'

RUN pip uninstall -y uvicorn
RUN pip install uvicorn[standard] gunicorn environs
RUN pip install csvkit
RUN pip install datasette
RUN pip install datasette-leaflet-geojson
RUN pip install datasette-block-robots

EXPOSE 5000

ADD app.py .
ADD settings.json .
ADD metadata.json .
COPY startup.sh .

ENTRYPOINT ["./startup.sh"]
