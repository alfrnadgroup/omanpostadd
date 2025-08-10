from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models import Address
from geoalchemy2.shape import to_shape
from shapely.geometry import mapping

router = APIRouter()

@router.get("/plots")
def get_plots(db: Session = Depends(get_db)):
    addresses = db.query(Address).all()
    if not addresses:
        # Return empty GeoJSON if no data found
        return {
            "type": "FeatureCollection",
            "features": []
        }

    features = []
    for address in addresses:
        if not address.geom:
            # Skip if no geometry
            continue

        try:
            geom_shape = to_shape(address.geom)
            geojson_geom = mapping(geom_shape)
        except Exception as e:
            # Skip invalid geometries but log if needed
            print(f"Invalid geometry for address id={address.id}: {e}")
            continue

        features.append({
            "type": "Feature",
            "geometry": geojson_geom,
            "properties": {
                "code": address.canonical_code,
                "wilayat_code": address.wilayat_code,
                # Add any other properties you want to expose
            }
        })

    return {
        "type": "FeatureCollection",
        "features": features
    }
