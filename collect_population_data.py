import requests
from rich import print  
from model import SessionLocal, Population, Country

session  = SessionLocal()

for country in session.query(Country.iso_3).filter(Country.iso_3 != '').distinct().all():
    country = country[0]
    print('country> ', country)
    resp = requests.get(
        f"https://api.worldbank.org/v2/country/{country}/indicator/SP.POP.TOTL",
        params={"format": "json", "date": "1960:2025"}
    )
    data = resp.json()
    print('length> ', len(data))
    if len(data) == 1:
        print(data)
        continue
    

    try:
        data = data[1]
        if data == None:
            continue

        for i in data:
            country_code, year, value = i['countryiso3code'], i['date'],  i['value']   
            print(country_code, year, value)
            record = (
                session.query(Population)
                .filter(Population.country_code == country_code)
                .filter(Population.year == year)
                .first()
            )
            if not record: record = Population()
            record.country_code = country_code
            record.year = year
            record.value = value
            session.add(record)
        session.commit()
    except Exception as e:
        print(e)
        print(data)
        print(len(data))
        break

