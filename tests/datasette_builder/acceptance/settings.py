"""Names shared by the acceptance fixtures and tests."""

import os

# The deployable image under test, built by `make image`.
IMAGE = os.environ.get("DATASETTE_IMAGE", "datasette-builder:local")
DATASETS_DIR = "/mnt/datasets"

# Always served by startup.sh.
CORE_DATABASES = ["digital-land", "performance"]
# Listed in the inspect file, so served. A plain SQLite database.
PUBLISHED_DATASET = "conservation-area"
# Listed in the inspect file, so served. Built like the pipeline's databases,
# with SpatiaLite metadata, a geometry column and a spatial index.
SPATIAL_DATASET = "tree-preservation-zone"
# On disk but not in the inspect file, so deliberately not served.
UNPUBLISHED_DATASET = "company"
