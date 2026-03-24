import time
from concurrent.futures import ThreadPoolExecutor, as_completed
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

# ── Multithreaded Trade Data ─────────────────────────────────────────── #
with engine.connect() as conn:
    # conn.execute(text("DROP TABLE IF EXISTS trade"))
    # conn.commit()
    
    countries_df = w.countries
    countries = w.countries.filter(pl.col("id") != "999")["id"].to_list()

    # Generate all pairs
    pairs = [(x, y) for x in countries for y in countries if x != y]

def fetch_trade_pair(args):
    """Thread worker: fetch one exporter→importer pair"""
    exporter, importer = args
    w = WorldTrade()
    w.exporting, w.importing = exporter, importer
    
    df = w.query()
    if df.is_empty():
        return None
    
    # Get country names (single-thread safe lookup)
    country_x_name = countries_df.filter(pl.col("id") == exporter)["name"][0]
    country_y_name = countries_df.filter(pl.col("id") == importer)["name"][0]
    
    print(f"{country_x_name} → {country_y_name}")
    print(df.height, "rows")
    
    # Add metadata for append
    df = df.with_columns([
        pl.lit(exporter).alias("reporter_iso3"),
        pl.lit(importer).alias("partner_iso3"),
        pl.lit(country_x_name).alias("reporter_name"),
        pl.lit(country_y_name).alias("partner_name")
    ])
    
    return df

# ── Run parallel (20 threads max - API safe) ────────────────────────── #
with ThreadPoolExecutor(max_workers=10) as executor:
    # Submit all pairs
    future_to_pair = {
        executor.submit(fetch_trade_pair, pair): pair 
        for pair in pairs
    }
    
    # Collect results as they complete
    for future in as_completed(future_to_pair):
        df = future.result()
        if df is not None:
            save(df, "trade", engine, if_exists="append")
        time.sleep(0.5)  # Gentle API throttling

print("✅ All trade pairs complete!")
