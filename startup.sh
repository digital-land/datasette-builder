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

DATASETTE_SERVE_ARGS="-h 0.0.0.0 -p 5000 --immutable=/app/entity.sqlite3 --immutable=/app/digital-land.sqlite3 "
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
        curl -qsfL -o $path "$url"  || continue
        set +x
    fi
    DATASETTE_SERVE_ARGS+="--immutable=/app/$dataset.sqlite3 "
done < <(csvcut -c dataset,collection specification/dataset.csv | tail -n +2)
IFS=$OLDIFS

set -x
date
set +x

echo -e "Artifacts downloaded:\n$(ls -lh /app/*.sqlite3)"
echo "Artifact ingestion complete, starting datasette service"
echo "Running: datasette serve ${DATASETTE_SERVE_ARGS}"

datasette serve ${DATASETTE_SERVE_ARGS}
# gunicorn app:app -t 60 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:5000
