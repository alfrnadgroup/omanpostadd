# models.py
from sqlalchemy import Column, Integer, String, Text, JSON, DateTime
from sqlalchemy.dialects.postgresql import UUID
from geoalchemy2 import Geometry
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class RawPlot(Base):
    __tablename__ = "raw_plots"

    raw_id = Column(UUID(as_uuid=True), primary_key=True)
    source = Column(Text)
    source_id = Column(Text)
    payload = Column(JSON)
    geom = Column(Geometry(geometry_type='GEOMETRY', srid=4326))
    footprint = Column(Geometry(geometry_type='GEOMETRY', srid=4326))
    fetched_at = Column(DateTime, default=datetime.utcnow)

class Address(Base):
    __tablename__ = "addresses"

    address_id = Column(Integer, primary_key=True, autoincrement=True)
    raw_id = Column(UUID(as_uuid=True))
    wilayat_code = Column(String)
    canonical_code = Column(String)
    geom = Column(Geometry(geometry_type='GEOMETRY', srid=4326))
    created_at = Column(DateTime, default=datetime.utcnow)
