import pandas as pd
import pycountry
import pycountry_convert as pc
import json
import csv
from rich import print  


# Read CSV file (Pandas - your preferred data engineering approach)
df = pd.read_csv('./data/world-countries-centroids.csv')
df.columns = df.columns.str.lower()
print(df.head())


result = []
for i in df.itertuples():
    try:
        country = pycountry.countries.get(alpha_2=i.iso.upper())
        alpha_3 = country.alpha_3
        numeric = country.numeric
    except:
        alpha_3 = ''
        numeric = ''

    try:
        continent_code = pc.country_alpha2_to_continent_code(country.alpha_2)
        continent_name = pc.convert_continent_code_to_continent_name(continent_code)
    except:
        continent_code = ''
        continent_name =''

    result.append({
        'iso_2': i.iso,
        'iso_3': alpha_3,
        'numeric': numeric,
        'name': i.country,
        'affiliation': i.countryaff,
        'affiliation_iso_2': i.aff_iso,
        'lat': i.latitude,
        'lon': i.longitude,
        'continent_code': continent_code,
        'continent_name': continent_name,
    })

path = './data/countries_by_iso3.json'
with open(path, 'w', encoding='utf-8') as f:
    json.dump(result, f, indent=2, ensure_ascii=False)

df = pd.read_json(path)  # orient='index' for ISO3 keys

# duplicates_count = df['iso_3'].duplicated().count()
# print(f"\nDuplicates in '{'iso_3'}': {duplicates_count}")

duplicate_mask = df['iso_3'].duplicated()
duplicate_rows = df[duplicate_mask == True]

print("Duplicate iso_3 rows:")
print(duplicate_rows.head().sort_values('iso_2'))