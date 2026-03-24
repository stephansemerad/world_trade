import time
from world_trade import WorldTrade
from sqlalchemy import create_engine, text
import polars as pl


DB_PATH = "sqlite:///trade.db"


# ── helpers ───────────────────────────────────────────────────────────── #
def save(df, table: str, engine, if_exists="replace"):
    df.to_pandas().to_sql(table, engine, if_exists=if_exists, index=False)


engine = create_engine(DB_PATH)
w = WorldTrade()

save(w.countries, "countries", engine)
save(w.products, "products", engine)

# ── 3. Trade data ─────────────────────────────────────────────────── #
# Drop the trade table so we start fresh on each run.
with engine.connect() as conn:
    # conn.execute(text("DROP TABLE IF EXISTS trade"))
    # conn.commit()
    w = WorldTrade()
    countries_df = w.countries
    countries = w.countries.filter(pl.col("id") != "999")["id"].to_list()

    gcc_iso3_codes = ['ARE', 'BHR', 'KWT', 'OMN', 'QAT', 'SAU', 'IRN']

    for x in gcc_iso3_codes:
        for y in countries:
            if x == y:
                continue

            w.exporting, w.importing = x, y

            df = w.query()
            if df.is_empty():
                continue
            else:
                country_x_name = countries_df.filter(pl.col("id") == w.exporting)[
                    "name"
                ][0]
                country_y_name = countries_df.filter(pl.col("id") == w.importing)[
                    "name"
                ][0]

                print(country_x_name, country_y_name)
                print(df)

                save(df, "trade", engine, if_exists="append")
                time.sleep(2)
