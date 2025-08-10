import os
import glob
import json
import logging
from fastkml import kml
from shapely.geometry import mapping
from shapely.wkt import dumps as wkt_dumps
import psycopg2
from psycopg2.extras import Json

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

def connect(dsn):
    return psycopg2.connect(dsn)

def ensure_tables(conn):
    with conn.cursor() as cur:
        cur.execute("""
            CREATE EXTENSION IF NOT EXISTS postgis;
            CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
            CREATE TABLE IF NOT EXISTS raw_plots (
                raw_id uuid DEFAULT uuid_generate_v4() PRIMARY KEY,
                source TEXT,
                source_id TEXT,
                payload JSONB,
                geom geometry(Geometry,4326),
                footprint geometry(Geometry,4326),
                fetched_at timestamptz DEFAULT now()
            );
            CREATE INDEX IF NOT EXISTS raw_plots_geom_idx ON raw_plots USING GIST(geom);
        """)
        conn.commit()

def parse_kml_file(path):
    with open(path, "rb") as f:
        doc = f.read()
    k_obj = kml.KML()
    k_obj.from_string(doc)
    features = list(k_obj.features())
    placemarks = []
    def walk(feats):
        for feat in feats:
            if hasattr(feat, "features"):
                walk(list(feat.features()))
            else:
                placemarks.append(feat)
    walk(features)
    return placemarks

def placemark_to_record(pm):
    props = {}
    if pm.name:
        props["name"] = pm.name
    if pm.description:
        props["description"] = pm.description
    if getattr(pm, "extended_data", None):
        try:
            for data in pm.extended_data.elements:
                props[data.name] = data.value
        except Exception as e:
            logging.warning(f"Failed to parse extended_data for {pm.name}: {e}")
    geom = pm.geometry
    footprint_geojson = mapping(geom) if geom else None
    return props, geom, footprint_geojson

def upsert(conn, source, source_id, props, geom, footprint):
    with conn.cursor() as cur:
        geom_wkt = wkt_dumps(geom) if geom else None
        footprint_json = json.dumps(footprint) if footprint else None
        cur.execute("""
            INSERT INTO raw_plots (source, source_id, payload, geom, footprint)
            VALUES (%s, %s, %s,
                    ST_SetSRID(ST_GeomFromText(%s),4326),
                    ST_SetSRID(ST_GeomFromGeoJSON(%s),4326))
        """, (source, source_id, Json(props), geom_wkt, footprint_json))

def load_directory(kml_dir, dsn):
    conn = connect(dsn)
    ensure_tables(conn)
    files = glob.glob(os.path.join(kml_dir, "*.kml"))
    logging.info(f"Found {len(files)} KML files in {kml_dir}")
    for filepath in files:
        try:
            placemarks = parse_kml_file(filepath)
            logging.info(f"{filepath} has {len(placemarks)} placemarks")
            for idx, pm in enumerate(placemarks):
                props, geom, footprint = placemark_to_record(pm)
                source_id = f"{os.path.basename(filepath)}::{idx}"
                upsert(conn, "omanreal_kml", source_id, props, geom, footprint)
            conn.commit()
            logging.info(f"Committed {len(placemarks)} placemarks from {filepath}")
        except Exception as e:
            logging.error(f"Error parsing {filepath}: {e}")
            conn.rollback()
    conn.close()

def main():
    import sys
    if len(sys.argv) < 3:
        print("Usage: python parse_load.py ./kmls/ postgres://user:pass@host/db")
        return
    load_directory(sys.argv[1], sys.argv[2])

if __name__ == "__main__":
    main()
