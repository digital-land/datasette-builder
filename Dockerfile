FROM python:3.10
RUN mkdir -p app
WORKDIR /app

RUN apt-get update && \
    apt-get install -y python3-dev gcc libsqlite3-mod-spatialite jq && \
    rm -rf /var/lib/apt/lists/*

ENV SQLITE_EXTENSIONS '/usr/lib/x86_64-linux-gnu/mod_spatialite.so'
COPY requirements/requirements.txt .
RUN pip install -r requirements.txt

EXPOSE 5000
ENV PORT=5000

COPY startup.sh .

COPY templates /app/templates

RUN groupadd --system appuser && \
    useradd --system --gid appuser --no-create-home appuser && \
    chown -R appuser:appuser /app

USER appuser

ENTRYPOINT ["bash", "startup.sh"]
