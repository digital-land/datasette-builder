.load /usr/lib/x86_64-linux-gnu/mod_spatialite.so

BEGIN;

SELECT InitSpatialMetadata(1);
SELECT AddGeometryColumn('geography', 'geom', 4326, 'MULTIPOLYGON', 2);
UPDATE geography SET geom = GeomFromText(geometry, 4326);
UPDATE geography SET geometry= AsGeoJSON(geom);
SELECT CreateSpatialIndex("geography", "geom");
DROP TABLE IF EXISTS KNN;
DROP TABLE IF EXISTS v_geography_simplified;

SELECT count(*) AS geography_count FROM geography;

CREATE TABLE v_geography_simplified
AS
SELECT
    g.rowid AS rowid,
    json_object('type', 'Feature', 'id', g.rowid, 'properties', json_object('name', g.name, 'type', g.type, 'slug', s.slug, 'rowid', g.rowid, 'entry-date', entry_date, 'start-date', start_date, 'end-date', end_date), 'geometry', json(AsGeoJSON(Simplify(g.geom, 0.0005)))) AS simple_features,
    json_object('type', 'Feature', 'id', g.rowid, 'properties', json_object('name', g.name, 'type', g.type, 'slug', s.slug, 'rowid', g.rowid, 'entry-date', entry_date, 'start-date', start_date, 'end-date', end_date), 'geometry', json(AsGeoJSON(geom))) AS features
FROM
    geography AS g
JOIN slug AS s ON g.slug_id = s.id
WHERE json_valid(AsGeoJSON(g.geom)) = 1;

SELECT count(*) FROM v_geography_simplified;

COMMIT;
