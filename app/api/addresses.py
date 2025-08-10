from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models import Address
from geoalchemy2.shape import to_shape

router = APIRouter()

@router.get("/addresses/{code}")
def get_address_by_code(code: str, db: Session = Depends(get_db)):
    address = db.query(Address).filter(Address.canonical_code == code).first()
    if not address:
        raise HTTPException(status_code=404, detail="Address not found")
    geom_shape = to_shape(address.geom)
    coords = list(geom_shape.coords) if hasattr(geom_shape, "coords") else []
    return {
        "address_id": address.address_id,
        "canonical_code": address.canonical_code,
        "wilayat_code": address.wilayat_code,
        "coordinates": coords
    }
