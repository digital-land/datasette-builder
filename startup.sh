#!/usr/bin/env bash

# Activate the virtual environment
source .venv/bin/activate

# Perform environment variable substitution for metadata.json if deployed
if [[ ! -z "$ENVIRONMENT" ]]; then
  envsubst < metadata_template.json > metadata.json
fi

exec datasette serve --metadata metadata.json -h 0.0.0.0 -p $PORT
