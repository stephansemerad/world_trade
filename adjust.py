from model import Product, Trade, SessionLocal, API_status, Country, Product
from sqlalchemy import text
from sqlalchemy.orm import aliased
from rich import print
reporter_country = aliased(Country)
partner_country = aliased(Country)

session = SessionLocal()

products = session.query(Product).all()
for product in products:
    print(f'checking > {product.id} - {product.name}')