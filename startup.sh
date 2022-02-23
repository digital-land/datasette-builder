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

IFS=,
csvcut -c dataset,collection specification/dataset.csv |
    tail -n +2 |
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
done

set -x
date
set +x

gunicorn app:app -t 60 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:5000
