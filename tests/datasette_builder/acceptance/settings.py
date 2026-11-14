"""Names shared by the acceptance fixtures and tests."""

import os

IMAGE = os.environ.get("DATASETTE_IMAGE", "datasette-builder:local")
DATASETS_DIR = "/mnt/datasets"

# Always served by startup.sh.
CORE_DATABASES = ["digital-land", "performance"]
# Listed in the inspect file, so served.
PUBLISHED_DATASET = "conservation-area"
# On disk but not in the inspect file, so deliberately not served.
UNPUBLISHED_DATASET = "company"
