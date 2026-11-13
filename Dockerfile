FROM python:3.13-slim
RUN mkdir -p app
WORKDIR /app

RUN apt-get update && \
    apt-get install -y python3-dev gcc jq && \
    rm -rf /var/lib/apt/lists/*

COPY requirements/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 5000
ENV PORT=5000

COPY startup.sh .

COPY templates /app/templates

RUN groupadd --system appuser && \
    useradd --system --gid appuser --no-create-home appuser && \
    chown -R appuser:appuser /app

USER appuser

ENTRYPOINT ["bash", "startup.sh"]
