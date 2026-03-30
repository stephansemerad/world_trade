from model import SessionLocal, Country, Trade, Product
from sqlalchemy.orm import aliased

session = SessionLocal()

reporter_country = aliased(Country)
partner_country = aliased(Country)
query = (
    session.query(
        Trade,
        Trade.reporter,
        Trade.partner,
        reporter_country.name.label("reporter_name"),
        reporter_country.lat.label("reporter_lat"),
        reporter_country.lon.label("reporter_lng"),

        partner_country.name.label("partner_name"),
    )
    .join(reporter_country, reporter_country.iso_3 == Trade.reporter)
    .join(partner_country, partner_country.iso_3 == Trade.partner)
    .filter(reporter_country.iso_3 == 'MEX')
      .distinct()  # Example filter for United States Minor Outlying Islands
    
).all()


result = []
for i in query:
    print(i.reporter, i.partner, i.reporter_name, i.partner_name)
