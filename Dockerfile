FROM python:3.10-slim
RUN mkdir -p app
WORKDIR /app

RUN apt-get update && \
    apt-get install -y python3-dev gcc libsqlite3-mod-spatialite jq && \
    rm -rf /var/lib/apt/lists/*

ENV SQLITE_EXTENSIONS '/usr/lib/x86_64-linux-gnu/mod_spatialite.so'
COPY requirements/requirements.txt .
RUN pip install -r requirements.txt

# DuckDB extensions for the Delta views - installed at build time because the
# datasette-parquet plugin stops DuckDB downloading anything at runtime
ENV DUCKDB_EXTENSION_DIRECTORY=/app/duckdb_extensions
RUN python -c "import duckdb; c = duckdb.connect(config={'extension_directory': '/app/duckdb_extensions'}); [c.execute(f'INSTALL {e}') for e in ('httpfs', 'aws')]"

EXPOSE 5000
ENV PORT=5000

COPY startup.sh .

COPY templates /app/templates

COPY bin /app/bin

RUN groupadd --system appuser && \
    useradd --system --gid appuser --no-create-home appuser && \
    chown -R appuser:appuser /app

USER appuser

ENTRYPOINT ["bash", "startup.sh"]
