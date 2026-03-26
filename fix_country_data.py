

middle_east_iso2 = [
    "BH",  # Bahrain
    "CY",  # Cyprus
    "EG",  # Egypt
    "IR",  # Iran
    "IQ",  # Iraq
    "IL",  # Israel
    "JO",  # Jordan
    "KW",  # Kuwait
    "LB",  # Lebanon
    "OM",  # Oman
    "PS",  # Palestine
    "QA",  # Qatar
    "SA",  # Saudi Arabia
    "SY",  # Syria
    "TR",  # Turkey
    "AE",  # United Arab Emirates
    "YE",  # Yemen
]


from model import Country, SessionLocal

for i in middle_east_iso2:
    country = session.query(Country).filter(Country.iso_2==i).first()
    print(country.name)
    country.continent_name = 'Middle-East'
    session.add(country)
    session.commit()


middle_east = session.query(Country).filter(Country.continent_name == 'Middle-East').all()
print(len(middle_east))
print(len(middle_east_iso2))


session = SessionLocal()

# UM United States Minor Outlying Islands → Oceania (Pacific islands)
# PN Pitcairn → Oceania (Pacific islands)
# AQ Antarctica → Antarctica (its own continent)
# SX Sint Maarten → North America (Caribbean)
# TF French Southern Territories → Africa (or sometimes grouped under “Antarctic” regions, but ISO‑based continent lists usually assign it to Africa)
# VA Vatican City → Europe (enclave within Rome, Italy)
# TL Timor‑Leste → Oceania (or sometimes grouped in “Asia” geopolitically, but most continent‑coding systems place it in Ocean


continents = session.query(Country.continent_name).distinct().all()
continents = [x.continent_name for x in continents]
print(continents)
countries = session.query(Country).filter(Country.continent_name == '').all()
for i in countries:
    print(i.iso_2, i.name)
    if i.iso_2 in ['UM', 'PN', 'TL']: i.continent_name = 'Oceania'
    if i.iso_2 in ['AQ']: i.continent_name = 'Antarctica'
    if i.iso_2 in ['SX']: i.continent_name = 'North America'
    if i.iso_2 in ['TF']: i.continent_name = 'Africa'
    if i.iso_2 in ['VA']: i.continent_name = 'Europe'
    session.add(i)
    session.commit()
