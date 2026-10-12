#!/usr/bin/env bash

DATASETTE_PID=0
DELTA_DIR=/tmp/delta

build_delta_views() {
  # Serve the PySpark collections' Delta tables through the datasette-parquet plugin.
  # Only where ENABLE_DELTA=true - if building the views fails, Datasette serves the
  # SQLite databases exactly as before. Runs on every restart to pick up new snapshots.
  DELTA_ARGS=""
  rm -f "$DELTA_DIR/datasets.txt"

  if [[ "${ENABLE_DELTA:-false}" != "true" ]]; then
    return
  fi

  if python bin/build_delta_views.py; then
    DELTA_ARGS="--metadata=$DELTA_DIR/metadata.json "
  else
    echo "Could not build Delta views, serving SQLite databases only"
    rm -f "$DELTA_DIR/datasets.txt"
  fi
}

start_datasette() {
  build_delta_views

  DATASETTE_SERVE_ARGS="-h 0.0.0.0 -p $PORT --setting default_cache_ttl 21600 --setting sql_time_limit_ms 10000 --setting allow_download off --setting allow_facet off --nolock --cors --immutable=/mnt/datasets/digital-land.sqlite3 --immutable=/mnt/datasets/performance.sqlite3 "

  for KEY in $(jq -rc 'keys[]' /mnt/datasets/inspect-data-all.json); do
    # a Delta-backed database takes the dataset's name, so leave out its SQLite file
    if grep -qxF "$KEY" "$DELTA_DIR/datasets.txt" 2>/dev/null; then
      continue
    fi
    DATASETTE_SERVE_ARGS+="--immutable=/mnt/datasets/$KEY.sqlite3 ";
  done

  echo "Found datasets for datasette $(jq -c 'keys | flatten' /mnt/datasets/inspect-data-all.json)"

  DATASETTE_SERVE_ARGS+="$DELTA_ARGS"
  DATASETTE_SERVE_ARGS+=" --inspect-file=/mnt/datasets/inspect-data-all.json --template-dir=/app/templates/"
  echo "Starting datasette service with args $DATASETTE_SERVE_ARGS"
  if [[ "$DATASETTE_PID" -ne "0" ]]; then
    kill $DATASETTE_PID
    sleep 5 # Wait for the service to stop
  fi
  datasette serve ${DATASETTE_SERVE_ARGS} & DATASETTE_PID=$! || exit 1
  echo "Datasette started with PID $DATASETTE_PID"
}

get_inspection_hash() {
  echo "$(cat /mnt/datasets/inspect-data-all.json)--$(ls -al /mnt/datasets/inspect-data-all.json)" | sha256sum
}

start_datasette

CURRENT_CHECKSUM=$(get_inspection_hash)

while [[ 1=1 ]]; do
  if [ "$CURRENT_CHECKSUM" == "$(get_inspection_hash)" ]; then
    true
  else
    echo "/mnt/datasets/inspect-data-all.json has changed, restarting datasette"
    CURRENT_CHECKSUM=$(get_inspection_hash)
    start_datasette
  fi
  sleep 2
done
