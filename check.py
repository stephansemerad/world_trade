import comtradeapicall
import pandas as pd
from rich import print  

# https://en.wikipedia.org/wiki/ISO_3166-1_numeric

# USA ↔ Canada Bilateral Trade (FIXED: all required params)
countries = {
    'usa': '840',    # USA (UN code)
    'canada': '124'  # Canada (UN code)
}

usa = comtradeapicall.convertCountryIso3ToCode('USA')
canada = comtradeapicall.convertCountryIso3ToCode('CAN')

print('canada> ', canada)
print('usa> ', usa)

# USA Petroleum Exports to Canada (HS 2709)
df = comtradeapicall.previewFinalData(
    typeCode='C',           # Product type. Goods (C) or Services (S)
    freqCode='A',           # Annual (A) or Monthly (M)
    clCode='HS',            # product classification used and which version (HS, SITC)
    period='2024',
    reporterCode=124,
    partnerCode=842,
    cmdCode='2709',         # Petroleum/crude ( Product code in conjunction with classification code)
    flowCode='X',           # Exports (Trade flow or sub-flow (exports, re-exports, imports, re-imports, etc.)
    includeDesc=True,
    partner2Code =0,
    customsCode=None,
    motCode=None,
)
print(df)
print(df.columns)

df = df.loc[:, df.nunique() > 1]
print(df)
# rows = df.to_dict(orient='records')
# for row in rows:
#     print(row)