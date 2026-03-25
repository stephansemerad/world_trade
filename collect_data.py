import time
import polars as pl
from world_trade import WorldTrade
from model import SessionLocal, Country
from rich import print  
import pycountry    
import pycountry_convert as pc

w = WorldTrade()
session = SessionLocal()

# Countries 
# -------------------------------------------------------------------------
for i in w.countries.iter_rows(named=True):
    c = Country()

    c.iso3 = i['id']
    c.name = i['name']

    if c.iso3 in ['999']: 
        continue
    else:
        print(c.iso3, c.name)
        
        country = pycountry.countries.get(alpha_3=c.iso3)
        if country:
            c.iso2 = country.alpha_2 if country else None
            
            continent_code = pc.country_alpha2_to_continent_code(country.alpha_2)
            if continent_code:
                continent_name = pc.convert_continent_code_to_continent_name(continent_code)  # Fixed!
                c.region = continent_name
            



# save(w.countries, "countries", engine)
# save(w.products, "products", engine)

# # ── 3. Trade data ─────────────────────────────────────────────────── #
# # Drop the trade table so we start fresh on each run.
# with engine.connect() as conn:
#     # conn.execute(text("DROP TABLE IF EXISTS trade"))
#     # conn.commit()
#     w = WorldTrade()
#     countries_df = w.countries
#     countries = w.countries.filter(pl.col("id") != "999")["id"].to_list()

#     gcc_iso3_codes = ['ARE', 'SGP']

#     for x in gcc_iso3_codes:
#         for y in countries:
#             if x == y:
#                 continue

#             w.exporting, w.importing = x, y

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
