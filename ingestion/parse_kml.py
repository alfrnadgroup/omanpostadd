# parse_kml.py
import os
import glob
from fastkml import kml
from shapely.geometry import mapping
from shapely.wkt import dumps as wkt_dumps

def parse_kml_file(filepath):
    with open(filepath, "rb") as f:
        data = f.read()

    k = kml.KML()
    k.from_string(data)
    features = list(k.features())

    placemarks = []

    def extract_features(features):
        for f in features:
            if hasattr(f, "features"):
                extract_features(list(f.features()))
            else:
                placemarks.append(f)

    extract_features(features)
    return placemarks

def placemark_to_dict(pm):
    props = {}
    if pm.name:
        props["name"] = pm.name
    if pm.description:
        props["description"] = pm.description
    if hasattr(pm, "extended_data") and pm.extended_data:
        try:
            for data in pm.extended_data.elements:
                props[data.name] = data.value
        except Exception:
            pass

    geom_wkt = None
    if pm.geometry:
        geom_wkt = wkt_dumps(pm.geometry)

    return {
        "properties": props,
        "geometry_wkt": geom_wkt
    }

def parse_dir(kml_dir):
    results = []
    for path in glob.glob(os.path.join(kml_dir, "*.kml")):
        try:
            pms = parse_kml_file(path)
            for i, pm in enumerate(pms):
                d = placemark_to_dict(pm)
                d["source_file"] = os.path.basename(path)
                d["source_index"] = i
                results.append(d)
        except Exception as e:
            print(f"[ERROR] parsing {path}: {e}")
    return results

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python parse_kml.py kml_directory")
        exit(1)
    parsed = parse_dir(sys.argv[1])
    print(f"Parsed {len(parsed)} placemarks.")
    for p in parsed[:5]:
        print(p)
