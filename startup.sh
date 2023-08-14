#!/usr/bin/env bash

DATASETTE_PID=0

start_datasette() {
  DATASETTE_SERVE_ARGS="-h 0.0.0.0 -p $PORT --setting sql_time_limit_ms 5000 --nolock --immutable=/mnt/datasets/entity.sqlite3 --immutable=/mnt/datasets/digital-land.sqlite3 "

  for KEY in $(jq -rc 'keys[]' /mnt/datasets/inspect-data-all.json); do
    DATASETTE_SERVE_ARGS+="--immutable=/mnt/datasets/$KEY.sqlite3 "
  done

  echo "Found datasets for datasette $(jq -c 'keys | flatten' /mnt/datasets/inspect-data-all.json)"

  DATASETTE_SERVE_ARGS+=" --inspect-file=/mnt/datasets/inspect-data-all.json --template-dir=/app/templates/"
  echo "Starting datasette service with args $DATASETTE_SERVE_ARGS"
  if [[ "$DATASETTE_PID" -ne "0" ]]; then
    kill $DATASETTE_PID
    sleep 5 # Wait for the service to stop
  fi
  datasette serve ${DATASETTE_SERVE_ARGS} & DATASETTE_PID=$! || exit 1
  sleep 5 # Wait for the service to start
  echo "waiting"
  echo "Datasette started with PID $DATASETTE_PID"
}

get_inspection_hash() {
  echo "$(cat /mnt/datasets/inspect-data-all.json)--$(ls -al /mnt/datasets/inspect-data-all.json)" | sha256sum
}

start_datasette

CURRENT_CHECKSUM=$(get_inspection_hash)

while [[ 1=1 ]]; do
  if [ "$CURRENT_CHECKSUM" == "$(get_inspection_hash)" ]; then
    echo "checksums match"
    true
  else
    echo "/mnt/datasets/inspect-data-all.json has changed, restarting datasette"
    CURRENT_CHECKSUM=$(get_inspection_hash)
    start_datasette
  fi
  sleep 2
done
