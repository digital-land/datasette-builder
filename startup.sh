#!/usr/bin/env bash

# Activate the virtual environment
source .venv/bin/activate

# Perform environment variable substitution for metadata.json if deployed
if [[ -z "$ENVIRONMENT" ]]; then
  envsubst < metadata_template.json > metadata.json
fi

# Run the application (replace with the actual command)
exec datasette serve --metadata metadata.json --port 8001 --host 127.0.0.1
