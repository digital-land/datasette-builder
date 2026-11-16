"""
Builds a dataset database the way the digital-land pipeline does.

The pipeline (digital_land/package/sqlite.py in digital-land-python) loads
SpatiaLite and runs InitSpatialMetadata(1), AddGeometryColumn and
CreateSpatialIndex. InitSpatialMetadata alone creates virtual tables
(SpatialIndex, KNN2, ElementaryGeometries) that Datasette can't open without
SpatiaLite: serving such a file without it fails at startup with "It looks like
you're trying to load a SpatiaLite database without first loading the
SpatiaLite module". Tests use these databases so that failure, and the lockdown
around SpatiaLite, are both covered.

Stdlib only and self-contained: the acceptance tests run this module's source
inside the Docker image, the one place SpatiaLite is guaranteed to exist.
"""

import sqlite3

GEOMETRY = "MULTIPOLYGON (((0 0, 1 0, 1 1, 0 0)))"
POINT = "POINT (0.5 0.5)"


def create_spatial_dataset(path, extension="mod_spatialite"):
    conn = sqlite3.connect(path)
    conn.enable_load_extension(True)
    conn.load_extension(extension)
    conn.enable_load_extension(False)

    conn.execute("select InitSpatialMetadata(1)")
    # SpatiaLite 5.1 creates KNN2; the pipeline's files were built with a
    # version that created KNN. Include both, as the real files can have either.
    conn.execute("create virtual table if not exists KNN using VirtualKNN()")
    conn.execute(
        "create table entity ("
        " entity integer primary key, name text, geometry text, point text)"
    )
    conn.execute(
        "select AddGeometryColumn('entity', 'geometry_geom', 4326, 'MULTIPOLYGON', 2)"
    )
    conn.execute("select AddGeometryColumn('entity', 'point_geom', 4326, 'POINT', 2)")
    conn.execute(
        "insert into entity (name, geometry, point, geometry_geom, point_geom)"
        " values ('spatial entity', ?, ?,"
        " GeomFromText(?, 4326), GeomFromText(?, 4326))",
        (GEOMETRY, POINT, GEOMETRY, POINT),
    )
    conn.execute("select CreateSpatialIndex('entity', 'geometry_geom')")
    conn.execute("select CreateSpatialIndex('entity', 'point_geom')")
    conn.commit()
    conn.close()
    return path
