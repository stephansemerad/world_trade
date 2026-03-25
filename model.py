import time
from world_trade import WorldTrade
from sqlalchemy import create_engine, Column, String, Integer, Float, ForeignKey, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import polars as pl

DB_PATH = "sqlite:///trade.db"
engine = create_engine(DB_PATH)
Base = declarative_base()
SessionLocal = sessionmaker(bind=engine)

# ── 1. SQLAlchemy ORM Objects (3 Tables) ─────────────────────────────────── #
class Country(Base):
    __tablename__ = "countries"
    iso3 = Column(String(3), primary_key=True)
    iso2 = Column(String(2))
    name = Column(String, nullable=False)
    region = Column(String)
    lat = Column(Float)
    lon = Column(Float)
    population = Column(Integer)
    
    partner = relationship("Trade", foreign_keys="Trade.reporter", back_populates="partner")
    reporter = relationship("Trade", foreign_keys="Trade.partner", back_populates="reporter")

class Product(Base):
    __tablename__ = "products"
    code = Column(String, primary_key=True,)
    name = Column(String)
    description = Column(String)

class Trade(Base):
    __tablename__ = "trade"
    id = Column(Integer, primary_key=True, autoincrement=True)
    reporter = Column(String, ForeignKey("countries.iso3"), nullable=False)
    partner = Column(String, ForeignKey("countries.iso3"), nullable=False)
    product_id = Column(String, ForeignKey("products.code"), nullable=False)
    year = Column(Integer, nullable=False)
    value = Column(Float)

    # Relationships
    reporter_country = relationship("Country", foreign_keys=[reporter])
    partner_country = relationship("Country", foreign_keys=[partner])
    product = relationship("Product")

Base.metadata.drop_all(engine)
Base.metadata.create_all(engine)