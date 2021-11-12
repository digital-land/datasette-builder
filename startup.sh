#!/bin/bash

set -e

mkdir -p specification
curl -qfsL 'https://raw.githubusercontent.com/digital-land/specification/main/specification/dataset.csv' > specification/dataset.csv 

collection_s3="https://collection-dataset.s3.eu-west-2.amazonaws.com/"

dl_s3="https://digital-land-collection.s3.eu-west-2.amazonaws.com/"

declare -a datasets=("entity" 
                "digital-land"
                )
set -x
date
set +x

for dataset in "${datasets[@]}"
do
    url=$dl_s3$dataset.sqlite3
    path=$dataset.sqlite3

    if [ ! -f $path ] ; then
        set -x
        curl -qsfL -o $path "$url" &
        set +x
    fi
   # or do whatever with individual element of the array
done

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
        curl -qsfL -o $path "$url"
        set +x
    fi
done

set -x
date
set +x

gunicorn app:app -t 60 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:5000


