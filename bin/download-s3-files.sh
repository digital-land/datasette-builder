#!/usr/bin/env bash

mkdir -p localstack/bootstrap/local-collection-data

BUCKET=$1

# if bucket is provided then all files will be downloaded from the bucket  to give a mmore accurate
# representation but advise is to leave bucket blank
if [ -n "$BUCKET" ]; then
  echo "Downloading log directory from: $BUCKET"  
  aws s3 sync s3://$BUCKET_NAME/log ./localstack/bootstrap/local-collection-data/log
  done
else
  echo "The bucket variable is empty will download data from sample datasets using python"
  python bin/download_s3_files.py
fi

echo "All sqlite files downloaded successfully."