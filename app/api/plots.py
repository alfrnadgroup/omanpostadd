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
    features = []
    for address in addresses:
        geom_shape = to_shape(address.geom)
        geojson_geom = mapping(geom_shape)

        features.append({
            "type": "Feature",
            "geometry": geojson_geom,
            "properties": {
                "code": address.canonical_code,
                "wilayat_code": address.wilayat_code,
                # add other properties if needed
            }
        })

    return {
        "type": "FeatureCollection",
        "features": features
    }
