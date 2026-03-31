from model import Product, Trade, SessionLocal, API_status, Country, Product
from sqlalchemy import text
from sqlalchemy.orm import aliased
from rich import print
reporter_country = aliased(Country)
partner_country = aliased(Country)

session = SessionLocal()



countries = session.query(Country).all()
for product in countries:
    print(f'checking > {product.id} - {product.name}')

