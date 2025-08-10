# parse_load.py
import os
import glob
import json
from fastkml import kml
from shapely.geometry import mapping
from shapely.wkt import dumps as wkt_dumps
import psycopg2
from psycopg2.extras import Json

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
        except Exception:
            pass
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
            RETURNING raw_id
        """, (source, source_id, Json(props), geom_wkt, footprint_json))
        rid = cur.fetchone()[0]
        conn.commit()
        return rid

def load_directory(kml_dir, dsn):
    conn = connect(dsn)
    ensure_tables(conn)
    for filepath in glob.glob(os.path.join(kml_dir, "*.kml")):
        try:
            placemarks = parse_kml_file(filepath)
            print(f"{filepath} has {len(placemarks)} placemarks")
            for idx, pm in enumerate(placemarks):
                props, geom, footprint = placemark_to_record(pm)
                source_id = f"{os.path.basename(filepath)}::{idx}"
                upsert(conn, "omanreal_kml", source_id, props, geom, footprint)
        except Exception as e:
            print(f"[ERROR] parsing {filepath}: {e}")
    conn.close()

def main():
    import sys
    if len(sys.argv) < 3:
        print("Usage: python parse_load.py ./kmls/ postgres://user:pass@host/db")
        return
    load_directory(sys.argv[1], sys.argv[2])

if __name__ == "__main__":
    main()
