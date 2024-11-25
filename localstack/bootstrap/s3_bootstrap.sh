#!/usr/bin/env bash

set -euo pipefail

# enable debug
# set -x

echo "configuring s3"
echo "==================="
LOCALSTACK_HOST=localhost
AWS_REGION=eu-west-2

base_local_path="/etc/localstack/init/ready.d/"

create_bucket() {
    local BUCKET_NAME_TO_CREATE=$1
    awslocal --endpoint-url=http://${LOCALSTACK_HOST}:4566 s3api create-bucket --bucket ${BUCKET_NAME_TO_CREATE} --region ${AWS_REGION} --create-bucket-configuration LocationConstraint=${AWS_REGION}
#    awslocal --endpoint-url=http://${LOCALSTACK_HOST}:4566 s3api put-bucket-cors --bucket ${BUCKET_NAME_TO_CREATE} --cors-configuration file:///etc/localstack/init/ready.d/cors-config.json
}

upload_dir_to_bucket() {
    local LOCAL_PATH=$1
    local S3_URI=$2
    awslocal s3 sync ${LOCAL_PATH} ${S3_URI}
}

create_bucket "local-collection-data"
upload_dir_to_bucket "${base_local_path}/local-collection-data" "s3://local-collection-data"