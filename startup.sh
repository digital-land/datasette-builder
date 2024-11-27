#!/usr/bin/env bash
curl -v s3.amazonaws.com

# Perform environment variable substitution for metadata.json if deployed
if [[ ! -z "$COLLECTION_DATA_BUCKET" ]]; then
  envsubst < metadata_template.json > metadata.json
  echo "COLLECTION_DATA_BUCKET set so metadata.json created"
else
  echo "COLLECTION_DATA_BUCKET not set so metadata.json not created"
fi

DATASETTE_PID=0

start_datasette() {
  DATASETTE_SERVE_ARGS="-h 0.0.0.0 -p $PORT --setting sql_time_limit_ms 10000 --nolock --cors --immutable=/mnt/datasets/digital-land.sqlite3 --immutable=/mnt/datasets/performance.sqlite3 --metadata metadata.json "

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