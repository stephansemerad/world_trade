from model import Product, Trade, SessionLocal, API_status, Country
import pypopulation

session = SessionLocal()

countries = (
    session.query(Country)
    .filter(Country.population > 50_000_000)
    .order_by(Country.population.desc())



    .all()
)

for country in countries:
   print(country.name, round(country.population / 1_000_000))

print(len(countries))