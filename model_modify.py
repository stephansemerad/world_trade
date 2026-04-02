from sqlalchemy import Column, String, Integer, Float, text
from model import engine

# Example: add a new column to the existing SQLite table
with engine.connect() as conn:
    conn.execute(text("ALTER TABLE countries ADD COLUMN capital STRING"))
    conn.execute(text("ALTER TABLE countries ADD COLUMN capital_lat FLOAT"))
    conn.execute(text("ALTER TABLE countries ADD COLUMN capital_lat FLOAT"))

    conn.commit()
