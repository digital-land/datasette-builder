FROM python:3.8
RUN mkdir -p app
WORKDIR /app

RUN set -ex; \
    apt-get update; \
    apt-get install -y \
        awscli \
        python3-dev \
        gcc \
        libsqlite3-mod-spatialite; \
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
COPY startup.sh .

ARG COLLECTION_DATASET_BUCKET_NAME
ENV COLLECTION_DATASET_BUCKET_NAME=${COLLECTION_DATASET_BUCKET_NAME}

ARG AWS_ACCESS_KEY_ID
ENV AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
ARG AWS_SECRET_ACCESS_KEY
ENV AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
ARG AWS_DEFAULT_REGION
ENV AWS_DEFAULT_REGION=${AWS_DEFAULT_REGION}

ENTRYPOINT ["./startup.sh"]
