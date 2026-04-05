from sqlalchemy import Column, String, Integer, Float, text
from model import engine

# Rename a column in the trades table
with engine.connect() as conn:
    # conn.execute(text("ALTER TABLE trades RENAME COLUMN reporter TO exporter"))
    # conn.execute(text("ALTER TABLE trades RENAME COLUMN partner TO importer"))
    # conn.execute(text("ALTER TABLE trades drop COLUMN mode_of_transport"))
    # conn.execute(text("ALTER TABLE trades drop COLUMN weight"))
    conn.execute(text("DELETE FROM trades"))
    conn.commit()
