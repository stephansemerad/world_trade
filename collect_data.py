import time
import polars as pl
from world_trade import WorldTrade
from model import SessionLocal, Country, Product, Trade
from rich import print  
import pandas as pd
from datetime import datetime
import comtradeapicall

session = SessionLocal()

# Trade 
# -------------------------------------------------------------------------
countries_name = {
    x.iso_3: x.name for x in 
    session.query(Country.iso_3, Country.name)
    .filter(Country.affiliation_iso_2 == Country.iso_2)
    .all()
}

countries_reporter = (
    session.query(Country)
    .filter(Country.affiliation_iso_2 == Country.iso_2)
    .filter(Country.un_code != None)
    .filter(Country.continent_name == 'Middle-East')
    .order_by(Country.population.desc())
    .all()
)

countries_partner = (
    session.query(Country)
    .filter(Country.affiliation_iso_2 == Country.iso_2)
    .filter(Country.un_code != None)
    .filter(Country.population > 100_000_000)
    .order_by(Country.population.desc())
    .all()
)

total = 0
for reporter in countries_reporter:
    for partner in countries_partner:
        if reporter.iso_3 == partner.iso_3:
            continue
        else:
            total += 1

products = session.query(Product).filter(Product.id == '2709').all()

trades = [f'{x.year}-{x.product_id}-{x.reporter}-{x.partner}'.lower() for x in 
          session.query(Trade.year, Trade.product_id, Trade.reporter, Trade.partner).distinct().all()]

print(f'{len(trades)} trades in database')

periods = [2024, 2023, 2022, 2021, 2020, 2019]
for period in periods:
    for product in products:
        counter = 0
        for reporter in countries_reporter:
            for partner in countries_partner:
                counter += 1
                print(f'progress > {counter}/{total} {counter/total:.2%}')
                if reporter == partner:
                    print(f'ignoring > {reporter.iso_3} - {partner.iso_3}')
                    continue
                else:
                    slug = f'{period}-{product.id}-{reporter.iso_3}-{partner.iso_3}'.lower()
                    print(slug, countries_name[reporter.iso_3], '->', countries_name[partner.iso_3])

                    if slug in trades:
                        print(f'slug exists > {slug}')
                        continue
                    else:
                        print(period, reporter.un_code, partner.un_code)

                        df = comtradeapicall.previewFinalData(
                            typeCode='C',           # Product type. Goods (C) or Services (S)
                            freqCode='A',           # Annual (A) or Monthly (M)
                            clCode='HS',            # product classification used and which version (HS, SITC)
                            period=period,
                            reporterCode=reporter.un_code,
                            partnerCode=partner.un_code,
                            cmdCode=product.id,
                            flowCode='X',           # Exports (Trade flow or sub-flow (exports, re-exports, imports, re-imports, etc.)
                            includeDesc=True,
                            partner2Code =0,
                            customsCode=None,
                            motCode=None,
                        )
                        
                        print(df)
                        if df.empty:
                            trade = (
                                session.query(Trade)
                                .filter(Trade.product_id == product.id)
                                .filter(Trade.reporter == reporter.iso_3)
                                .filter(Trade.partner == partner.iso_3)
                                .filter(Trade.year == period)
                                .first()
                            )
                            if not trade: trade = Trade()

                            trade.product_id = product.id
                            trade.reporter = reporter.iso_3
                            trade.partner = partner.iso_3
                            trade.year = period
                            trade.value = None
                            trade.weight = None
                            trade.mode_of_transport = None
                            session.add(trade)
                            session.commit()
                        else:
                            for x in df.itertuples():
                                trade = (
                                    session.query(Trade)
                                    .filter(Trade.product_id == product.id)
                                    .filter(Trade.reporter == reporter.iso_3)
                                    .filter(Trade.partner == partner.iso_3)
                                    .filter(Trade.year == x.period)
                                    .filter(Trade.mode_of_transport == x.motDesc)
                                    .first()
                                )
                                if not trade:
                                    trade = Trade()

                                trade.product_id = product.id
                                trade.reporter = reporter.iso_3
                                trade.partner = partner.iso_3
                                trade.year = x.period
                                trade.value = x.primaryValue
                                trade.weight = x.netWgt
                                trade.mode_of_transport = x.motDesc

                                session.add(trade)
                                session.commit()
                

