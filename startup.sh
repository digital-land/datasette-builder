#!/bin/bash

set -x
date
set +x

mkdir -p specification
set -x
curl -qfsL 'https://raw.githubusercontent.com/digital-land/specification/main/specification/dataset.csv' > specification/dataset.csv
set -x

collection_s3="https://${COLLECTION_DATASET_BUCKET_NAME}.s3.eu-west-2.amazonaws.com/"

set -x
curl -qsfL -o digital-land.sqlite3 ${collection_s3}digital-land-builder/dataset/digital-land.sqlite3
curl -qsfL -o entity.sqlite3 ${collection_s3}entity-builder/dataset/entity.sqlite3

# test database for testing ..
curl -qsfL -o listed-building-grade.sqlite3 https://${COLLECTION_DATASET_BUCKET_NAME}.s3.eu-west-2.amazonaws.com/listed-building-collection/dataset/listed-building-grade.sqlite
set +x

DATASETTE_SERVE_ARGS="-h 0.0.0.0 -p 5000 --setting sql_time_limit_ms 2000 --immutable=/app/entity.sqlite3 --immutable=/app/digital-land.sqlite3 "
OLDIFS=$IFS
IFS=,
while read dataset collection
do
    # current s3 structure has collection, but should be flattend
    # https://${COLLECTION_DATASET_BUCKET_NAME}.s3.eu-west-2.amazonaws.com/{COLLECTION}-collection/dataset/{DATASET}/{DATASET}.sqlite3
    case "$collection" in
    ""|organisation) continue ;;
    esac

    url=$collection_s3$collection-collection/dataset/$dataset.sqlite3
    path=$dataset.sqlite3

    if [ ! -f $path ] ; then
        set -x
        curl -qsfL -o $path "$url" && DATASETTE_SERVE_ARGS+="--immutable=/app/$dataset.sqlite3 " || continue
        set +x
    fi

    inspect_file_url=$collection_s3$collection-collection/dataset/$dataset.sqlite3.json
    inspect_file_path=$dataset.sqlite3.json

    if [ ! -f $inspect_file_path ] ; then
        set -x
        curl -qsfL -o $inspect_file_path "$inspect_file_url" || continue
        set +x
    fi

done < <(csvcut -c dataset,collection specification/dataset.csv | tail -n +2)
IFS=$OLDIFS

set -x
date
set +x

echo -e "Artifacts downloaded:\n$(ls -lh /app/*.sqlite3)"
echo "Artifact ingestion complete. Generate inspect file for all databases"

./inspect.py /app

DATASETTE_SERVE_ARGS+=" --inspect-file=/app/inspect-data-all.json"

echo "Starting datasette service with args $DATASETTE_SERVE_ARGS"

datasette serve ${DATASETTE_SERVE_ARGS}
