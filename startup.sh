#!/usr/bin/env bash

DATASETTE_SERVE_ARGS="-h 0.0.0.0 -p $PORT --setting sql_time_limit_ms 5000 --nolock "
DATASETTE_PID=0

start_datasette() {
  for KEY in $(jq -rc 'keys[]' /mnt/datasets/inspect-data-all.json); do
    DATASETTE_SERVE_ARGS+="--immutable=/mnt/datasets/$KEY.sqlite3 "
  done

  echo "Found datasets for datasette $(jq -c 'keys | flatten' /mnt/datasets/inspect-data-all.json)"

  DATASETTE_SERVE_ARGS+=" --inspect-file=/mnt/datasets/inspect-data-all.json --template-dir=/app/templates/"
  echo "Starting datasette service with args $DATASETTE_SERVE_ARGS"
  if [[ "$DATASETTE_PID" -ne "0" ]]; then kill $DATASETTE_PID; fi
  datasette serve ${DATASETTE_SERVE_ARGS} & DATASETTE_PID=$! || exit 1
  echo "Datasette started with PID $DATASETTE_PID"
}

start_datasette
CURRENT_CHECKSUM=$(sha256sum /mnt/datasets/inspect-data-all.json)

while [[ 1=1 ]]; do
  if echo "$CURRENT_CHECKSUM" | sha256sum --check --status; then
    true
  else
    echo "/mnt/datasets/inspect-data-all.json has changed, restarting datasette"
    CURRENT_CHECKSUM=$(sha256sum /mnt/datasets/inspect-data-all.json)
    start_datasette
  fi
  sleep 10
done
