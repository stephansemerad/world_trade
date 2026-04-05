import time
from sqlalchemy import (
    create_engine,
    Column,
    String,
    Integer,
    Float,
    ForeignKey,
    DateTime,
)
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
    iso_3 = Column(String(3), primary_key=True)
    iso_2 = Column(String(2))
    numeric = Column(Integer)
    name = Column(String, nullable=False)
    un_code = Column(String, nullable=True)
    population = Column(Integer)

    capital = Column(String)
    capital_lat = Column(String)
    capital_lng = Column(String)

    affiliation = Column(String)
    affiliation_iso_2 = Column(String)

    lat = Column(Float)
    lon = Column(Float)

    continent_code = Column(String)
    continent_name = Column(String)
    # Now back_populates refers to relationships (not columns)
    trades_as_exporter = relationship(
        "Trade", foreign_keys="Trade.exporter", back_populates="exporter_country"
    )
    trades_as_importer = relationship(
        "Trade", foreign_keys="Trade.importer", back_populates="importer_country"
    )

    def as_dict(self) -> dict:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class Product(Base):
    __tablename__ = "products"
    id = Column(
        String,
        primary_key=True,
    )
    name = Column(String)
    category = Column(String)
    description = Column(String)

    def as_dict(self) -> dict:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class Trade(Base):
    __tablename__ = "trades"
    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(String, ForeignKey("products.id"), nullable=False)
    exporter = Column(String, ForeignKey("countries.iso_3"), nullable=False)
    importer = Column(String, ForeignKey("countries.iso_3"), nullable=False)
    year = Column(Integer, nullable=False)
    value = Column(Float)

    # Named relationships for back_populates
    exporter_country = relationship(
        "Country", foreign_keys=[exporter], back_populates="trades_as_exporter"
    )
    importer_country = relationship(
        "Country", foreign_keys=[importer], back_populates="trades_as_importer"
    )

    product = relationship("Product")

    def as_dict(self) -> dict:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class Population(Base):
    __tablename__ = "populations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    country_code = Column(String, ForeignKey("countries.iso_3"), nullable=False)
    year = Column(Integer, nullable=False)
    value = Column(Float)


# Base.metadata.drop_all(engine)
Base.metadata.create_all(engine)
