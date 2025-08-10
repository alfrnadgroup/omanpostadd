from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from app.api import addresses  # your existing API router

import glob
from fastkml import kml
import json
from shapely.geometry import mapping
import os

app = FastAPI(title="Oman Post Addressing System")

# Use absolute path for static directory, relative to current file location
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

app.include_router(addresses.router, prefix="/api")

plots = {}  # code -> plot info

def load_kmls():
    files = glob.glob(os.path.join(BASE_DIR, "../data/raw/*.kml"))
    seq = 1
    for file in files:
        with open(file, "rb") as f:
            doc = f.read()
        k = kml.KML()
        k.from_string(doc)
        features = list(k.features())

        def walk(feats):
            for feat in feats:
                if hasattr(feat, "features"):
                    yield from walk(list(feat.features()))
                else:
                    yield feat

        placemarks = list(walk(features))
        for pm in placemarks:
            code = f"OM-WL001-{seq:06d}"
            plots[code] = {
                "name": pm.name,
                "description": pm.description,
                "geometry": pm.geometry  # shapely geometry object
            }
            seq += 1

@app.on_event("startup")
def startup_event():
    load_kmls()

@app.get("/", response_class=HTMLResponse)
async def index():
    index_path = os.path.join(STATIC_DIR, "index.html")
    with open(index_path, "r") as f:
        return f.read()

@app.get("/api/plots")
async def get_plots():
    features = []
    for code, plot in plots.items():
        geom = plot["geometry"]
        geojson = mapping(geom) if geom else None
        if geojson:
            features.append({
                "type": "Feature",
                "geometry": geojson,
                "properties": {
                    "code": code,
                    "name": plot["name"]
                }
            })
    return {"type": "FeatureCollection", "features": features}

@app.get("/api/addresses/{code}")
async def get_address(code: str):
    if code not in plots:
        raise HTTPException(status_code=404, detail="Address not found")
    plot = plots[code]
    return {
        "code": code,
        "name": plot["name"],
        "description": plot["description"]
    }
