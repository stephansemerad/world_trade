from model import Product, Trade, SessionLocal, Country, Product
from sqlalchemy import text
from sqlalchemy.orm import aliased
from rich import print
reporter_country = aliased(Country)
partner_country = aliased(Country)

session = SessionLocal()


