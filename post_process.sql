.load /usr/lib/x86_64-linux-gnu/mod_spatialite.so

SELECT InitSpatialMetadata(1);

BEGIN;

/* SELECT AddGeometryColumn('geography', 'geom', 4326, 'MULTIPOLYGON', 2); */
/* UPDATE geography SET geom = GeomFromText(geometry, 4326); */
/* UPDATE geography SET geometry= AsGeoJSON(geom); */
/* SELECT CreateSpatialIndex("geography", "geom"); */
DROP TABLE IF EXISTS KNN;
/* DROP TABLE IF EXISTS v_geography_simplified; */

SELECT count(*) AS geography_count FROM geography;

DROP TABLE IF EXISTS geography_geom;
CREATE TABLE geography_geom (
    geojson_simple,
    geojson_full,
    type
);
SELECT AddGeometryColumn('geography_geom', 'geom', 4326, 'MULTIPOLYGON', 2);
SELECT AddGeometryColumn('geography_geom', 'geom_point', 4326, 'POINT', 2);

INSERT INTO geography_geom (rowid, geojson_simple, geojson_full, type, geom)
SELECT
    g.rowid AS rowid,
    json_object('type', 'Feature', 'id', g.rowid, 'properties', json_object('name', g.name, 'type', g.type, 'slug', s.slug, 'rowid', g.rowid, 'entry-date', entry_date, 'start-date', start_date, 'end-date', end_date), 'geometry', json(AsGeoJSON(Simplify(GeomFromText(g.geometry, 4326), 0.0005)))) AS geojson_simple,
    json_object('type', 'Feature', 'id', g.rowid, 'properties', json_object('name', g.name, 'type', g.type, 'slug', s.slug, 'rowid', g.rowid, 'entry-date', entry_date, 'start-date', start_date, 'end-date', end_date), 'geometry', json(AsGeoJSON(GeomFromText(g.geometry, 4326)))) AS geojson_full,
    g.type AS type,
    GeomFromText(g.geometry, 4326) AS geom
FROM
    geography AS g
JOIN slug AS s ON g.slug_id = s.id
WHERE json_valid(AsGeoJSON(GeomFromText(g.geometry))) = 1;

INSERT INTO geography_geom (rowid, geojson_simple, geojson_full, type, geom_point)
SELECT
    g.rowid AS rowid,
    json_object('type', 'Feature', 'id', g.rowid, 'properties', json_object('name', g.name, 'type', g.type, 'slug', s.slug, 'rowid', g.rowid, 'entry-date', entry_date, 'start-date', start_date, 'end-date', end_date), 'geometry', json(AsGeoJSON(Simplify(GeomFromText(g.point, 4326), 0.0005)))) AS geojson_simple,
    json_object('type', 'Feature', 'id', g.rowid, 'properties', json_object('name', g.name, 'type', g.type, 'slug', s.slug, 'rowid', g.rowid, 'entry-date', entry_date, 'start-date', start_date, 'end-date', end_date), 'geometry', json(AsGeoJSON(GeomFromText(g.point, 4326)))) AS geojson_full,
    g.type AS type,
    GeomFromText(g.point, 4326) AS geom_point
FROM
    geography AS g
JOIN slug AS s ON g.slug_id = s.id
WHERE json_valid(AsGeoJSON(GeomFromText(g.point))) = 1;

SELECT CreateSpatialIndex("geography_geom", "geom");
SELECT count(*) AS geography_count FROM geography_geom;

/* CREATE TABLE v_geography_simplified */
/* AS */
/* SELECT */
/*     g.rowid AS rowid, */
/*     json_object('type', 'Feature', 'id', g.rowid, 'properties', json_object('name', g.name, 'type', g.type, 'slug', s.slug, 'rowid', g.rowid, 'entry-date', entry_date, 'start-date', start_date, 'end-date', end_date), 'geometry', json(AsGeoJSON(Simplify(g.geom, 0.0005)))) AS simple_features, */
/*     json_object('type', 'Feature', 'id', g.rowid, 'properties', json_object('name', g.name, 'type', g.type, 'slug', s.slug, 'rowid', g.rowid, 'entry-date', entry_date, 'start-date', start_date, 'end-date', end_date), 'geometry', json(AsGeoJSON(geom))) AS features */
/* FROM */
/*     geography AS g */
/* JOIN slug AS s ON g.slug_id = s.id */
/* WHERE json_valid(AsGeoJSON(g.geom)) = 1; */

/* SELECT count(*) FROM v_geography_simplified; */

COMMIT;
