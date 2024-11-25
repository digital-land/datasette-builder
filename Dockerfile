FROM python:3.8
RUN mkdir -p app
WORKDIR /app

RUN apt-get update && \
    apt-get install -y python3-dev gcc libsqlite3-mod-spatialite jq gettext && \
    rm -rf /var/lib/apt/lists/*

ENV SQLITE_EXTENSIONS '/usr/lib/x86_64-linux-gnu/mod_spatialite.so'
RUN pip install -U datasette
RUN pip install datasette-block-robots
RUN pip uninstall -y uvicorn
RUN pip install uvicorn[standard] gunicorn
RUN pip install csvkit

COPY requirements.txt .
RUN pip3 install --upgrade -r requirements.txt

EXPOSE 5000
ENV PORT=5000

COPY startup.sh .
COPY metadata_template.json .

ADD templates /app/templates

ENTRYPOINT ["bash", "startup.sh"]
