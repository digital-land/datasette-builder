#!/bin/bash

set -x
date
set +x

mkdir -p specification
set -x
curl -qfsL 'https://raw.githubusercontent.com/digital-land/specification/main/specification/dataset.csv' > specification/dataset.csv
set -x

collection_s3="s3://${COLLECTION_DATASET_BUCKET_NAME}/"

set -x
s3 cp ${collection_s3}digital-land-builder/dataset/digital-land.sqlite3 digital-land.sqlite3
s3 cp ${collection_s3}entity-builder/dataset/entity.sqlite3 entity.sqlite3

# test database for testing ..
s3 cp s3://${COLLECTION_DATASET_BUCKET_NAME}/listed-building-collection/dataset/listed-building-grade.sqlite3 listed-building-grade.sqlite3
set +x

IFS=,
csvcut -c dataset,collection specification/dataset.csv |
    tail -n +2 |
while read dataset collection
do
    # current s3 structure has collection, but should be flattend
    # s3://${COLLECTION_DATASET_BUCKET_NAME}/{COLLECTION}-collection/dataset/{DATASET}/{DATASET}.sqlite3
    case "$collection" in
    ""|organisation) continue ;;
    esac

    uri=$collection_s3$collection-collection/dataset/$dataset.sqlite3
    path=$dataset.sqlite3

    if [ ! -f $path ] ; then
        set -x
        s3 cp "$uri" $path  || continue
        set +x
    fi
done

set -x
date
set +x

echo "Artifact ingestion complete, starting datasette service"

gunicorn app:app -t 60 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:5000
