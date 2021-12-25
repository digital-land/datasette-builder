#!/bin/bash

set -x
date
set +x

mkdir -p specification
set -x
curl -qfsL 'https://raw.githubusercontent.com/digital-land/specification/main/specification/dataset.csv' > specification/dataset.csv
set -x

collection_s3="https://collection-dataset.s3.eu-west-2.amazonaws.com/"

set -x
curl -qsfL -o digital-land.sqlite3 ${collection_s3}digital-land-builder/dataset/digital-land.sqlite3
curl -qsfL -o entity.sqlite3 ${collection_s3}entity-builder/dataset/entity.sqlite3
set +x

# don't download EAV datasets for now ..
if false
then
    IFS=,
    csvcut -c dataset,collection specification/dataset.csv |
        tail -n +2 |
        while read dataset collection
    do
        # current s3 structure has collection, but should be flattend
        # https://collection-dataset.s3.eu-west-2.amazonaws.com/{COLLECTION}-collection/issue/{DATASET}/{DATASET}.sqlite3
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
fi

set -x
date
set +x

gunicorn app:app -t 60 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:5000
