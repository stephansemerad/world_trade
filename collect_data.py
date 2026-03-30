import time
import polars as pl
from world_trade import WorldTrade
from model import SessionLocal, Country, Product, Trade, API_status
from rich import print  
import pandas as pd
from datetime import datetime


w = WorldTrade()
session = SessionLocal()

# # Countries 
# # -------------------------------------------------------------------------
# country_codes = [x.iso_2 for x in session.query(Country).all()]
# for i in pd.read_json('./data/countries_by_iso3.json').itertuples():
#     if i.iso_2 in country_codes:
#         continue
#     else:
#         country = session.query(Country).filter(Country.iso_2 == i.iso_2).first()
#         if not country:
#             country = Country()
        
#         country.iso_2 = i.iso_2
#         country.iso_3 = i.iso_3
#         country.numeric = i.numeric
#         country.name = i.name
#         country.affiliation = i.affiliation
#         country.affiliation_iso_2 = i.affiliation_iso_2
#         country.lat = i.lat
#         country.lon = i.lon
#         country.continent_code = i.continent_code
#         country.continent_name = i.continent_name

#         print(country.iso_2, country.name, country.continent_code, country.continent_name)

#         try:
#             session.add(country)
#             session.commit()  
#             print('updated country')
#         except Exception as e:
#             print(f'error {e}')
#             break


# # Products 
# # -------------------------------------------------------------------------
# product_codes = [x.id for x in session.query(Product).all()]
# for i in w.products.to_pandas().itertuples():
#     if i.id == '999999' or i.id in product_codes:
#         continue
#     else:
#         product = session.query(Product).filter(Product.id == i.id).first()
#         if not product:
#             product = Product()
        
#         product.id = i.id
#         product.name = i.name

#         print(product.id, product.name)

#         try:
#             session.add(product)
#             session.commit()  
#             print('updated product')
#         except Exception as e:
#             print(f'error {e}')
#             break






# Trade 
# -------------------------------------------------------------------------
countries_reporter = session.query(Country).all()
countries_partner = session.query(Country).all()

products = session.query(Product).filter(Product.id == 'Fuels').all()
trades = [f"{x.product_id}>{x.reporter}>{x.partner}" for x in session.query(Trade).all()]

for product in products:
    for reporter in countries_reporter:
        for partner in countries_partner:
            slug = f'{product.id}-{reporter.iso_3}-{partner.iso_3}'.lower()
            
            api_check = session.query(API_status).filter(API_status.slug == slug).first()
            if api_check:
                print('skipping > ', slug, ' > already exists in API_status')
                continue

            if reporter.iso_3 == partner.iso_3:
                print(f'ignoring > {slug}')
                continue
            else:
                check = (
                    session.query(Trade)
                    .filter(Trade.product_id == product.id)
                    .filter(Trade.reporter == reporter.iso_3)
                    .filter(Trade.partner == partner.iso_3)
                    .first()
                )
                if check:
                    print(f'trade exists > {slug}')
                else: 
                    trade = Trade()

                    w.product, w.exporting, w.importing = product.id, reporter.iso_3, partner.iso_3
                    df = w.query()

                    for x in df.to_pandas().itertuples():
                        print(x)

                        trade = (
                            session.query(Trade)
                            .filter(Trade.product_id == product.id)
                            .filter(Trade.reporter == reporter.iso_3)
                            .filter(Trade.partner == partner.iso_3)
                            .filter(Trade.year == x.period)
                            .first()
                        )
                        if not trade:
                            trade = Trade()

                        trade.product_id = product.id
                        trade.reporter = reporter.iso_3
                        trade.partner = partner.iso_3
                        trade.year = x.period
                        trade.value = x.value

                    session.add(trade)
                    
                    print('slug', slug)
                    print('df> ', df.is_empty())

                    api_status = session.query(API_status).filter(API_status.slug == slug).first()
                    if not api_status:

                        api_status = API_status()
                        api_status.slug = slug
                        api_status.status = 'success' if not df.is_empty() else 'failed'
                        api_status.retrieved_at = datetime.now()
                        session.add(api_status)
                        session.commit()

                    
                    
                    






#     gcc_iso3_codes = ['ARE', 'SGP']

#     for x in gcc_iso3_codes:
#         for y in countries:
#             if x == y:
#                 continue

#             

#             df = w.query()
#             if df.is_empty():
#                 continue
#             else:
#                 country_x_name = countries_df.filter(pl.col("id") == w.exporting)[
#                     "name"
#                 ][0]
#                 country_y_name = countries_df.filter(pl.col("id") == w.importing)[
#                     "name"
#                 ][0]

#                 print(country_x_name, country_y_name)
#                 print(df)

#                 save(df, "trade", engine, if_exists="append")
#                 time.sleep(2)
