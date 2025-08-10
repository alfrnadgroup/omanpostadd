from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models import Address
from geoalchemy2.shape import to_shape
from shapely.geometry import mapping

router = APIRouter()

@router.get("/plots")
def get_plots(db: Session = Depends(get_db)):
    addresses = db.query(Address).all()
    print(f"[DEBUG] Found {len(addresses)} addresses in DB")

    if not addresses:
        # Return empty GeoJSON FeatureCollection if no data found
        return {
            "type": "FeatureCollection",
            "features": []
        }

    features = []
    for address in addresses:
        if not address.geom:
            print(f"[DEBUG] Address id={address.id} has no geometry, skipping")
            continue

        try:
            geom_shape = to_shape(address.geom)
            geojson_geom = mapping(geom_shape)
        except Exception as e:
            print(f"[WARNING] Invalid geometry for address id={address.id}: {e}")
            continue

        features.append({
            "type": "Feature",
            "geometry": geojson_geom,
            "properties": {
                "code": address.canonical_code,
                "wilayat_code": address.wilayat_code,
                # Add other desired properties here
            }
        })

    return {
        "type": "FeatureCollection",
        "features": features
    }
