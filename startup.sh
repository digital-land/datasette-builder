#!/usr/bin/env bash

DATASETTE_PID=0

validate_inspect_file() {
  INSPECT_KEYS=$(cat /mnt/datasets/inspect-data-all.json | jq -r 'keys[]')
  for KEY in $INSPECT_KEYS; do
    if [ ! -f "/mnt/datasets/$KEY.sqlite3" ]; then
      echo "WARNING: inspect file references $KEY but /mnt/datasets/$KEY.sqlite3 is missing — datasette will fall back to live EFS reads for this database"
    fi
  done
  for FILE in /mnt/datasets/*.sqlite3; do
    BASENAME=$(basename "$FILE" .sqlite3)
    if ! echo "$INSPECT_KEYS" | grep -qx "$BASENAME"; then
      echo "WARNING: $BASENAME.sqlite3 exists but has no entry in inspect file — datasette will fall back to live EFS reads for this database"
    fi
  done
}

start_datasette() {
  DATASETTE_SERVE_ARGS="-h 0.0.0.0 -p $PORT --setting default_cache_ttl 21600 --setting sql_time_limit_ms 10000 --setting allow_download off --setting allow_facet off --nolock --cors --immutable=/mnt/datasets/digital-land.sqlite3 --immutable=/mnt/datasets/performance.sqlite3 "

  for KEY in $(jq -rc 'keys[]' /mnt/datasets/inspect-data-all.json); do
    DATASETTE_SERVE_ARGS+="--immutable=/mnt/datasets/$KEY.sqlite3 ";
  done

  echo "Found datasets for datasette $(jq -c 'keys | flatten' /mnt/datasets/inspect-data-all.json)"

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
  # %s = file size in bytes, %Y = modification time as Unix timestamp
  stat -c '%s %Y' /mnt/datasets/inspect-data-all.json
}

validate_inspect_file
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
