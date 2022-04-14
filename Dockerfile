FROM python:3.8
RUN mkdir -p app
WORKDIR /app

RUN apt-get update && \
    apt-get install -y python3-dev gcc libsqlite3-mod-spatialite && \
    rm -rf /var/lib/apt/lists/*

ENV SQLITE_EXTENSIONS '/usr/lib/x86_64-linux-gnu/mod_spatialite.so'
RUN pip install -U datasette
RUN pip install datasette-block-robots
RUN pip uninstall -y uvicorn
RUN pip install uvicorn[standard] gunicorn
RUN pip install csvkit

EXPOSE 5000

COPY app.py .
COPY settings.json .
COPY metadata.json .
COPY inspect.py .
COPY startup.sh .

ARG COLLECTION_DATASET_BUCKET_NAME
ENV COLLECTION_DATASET_BUCKET_NAME=${COLLECTION_DATASET_BUCKET_NAME}

ENTRYPOINT ["./startup.sh"]
