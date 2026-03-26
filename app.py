import pandas as pd
import streamlit as st
from st_cytoscape import cytoscape
import altair as alt
import numpy as np
import plotly.express as px
import pydeck as pdk
from model import SessionLocal, Country, Product, Trade
from sqlalchemy.orm import aliased

session = SessionLocal()

st.set_page_config(page_title="World Trade Map", page_icon="🌐", layout="wide")
st.title("🌐 World Trade Map")
st.write("A simple interactive graph example.")


@st.cache_data
def load_countries():
    trade_partners_subq = session.query(Trade.partner.distinct()).subquery()

    query = (
        session.query(Country)
        .filter(Country.iso_3.in_(trade_partners_subq))
        .order_by(Country.name.desc())
    )
    df = pd.read_sql_query(query.statement, session.bind)
    return df

@st.cache_data
def load_products():
    query = (
        session.query(Product)
        .order_by(Product.id.desc())
    )
    df = pd.read_sql_query(query.statement, session.bind)
    return df

@st.cache_data
def load_trades(product_selection=None, country_selection=None, year=None):
    reporter_country = aliased(Country)
    partner_country = aliased(Country)
    query = (
        session.query(
            Trade,
            reporter_country.name.label("reporter_name"),
            reporter_country.lat.label("reporter_lat"),
            reporter_country.lon.label("reporter_lng"),

            partner_country.name.label("partner_name"),
            partner_country.lat.label("partner_lat"),
            partner_country.lon.label("partner_lng"),
        )
        .join(reporter_country, reporter_country.iso_3 == Trade.reporter)
        .outerjoin(partner_country, partner_country.iso_3 == Trade.partner)
        
    )
    if product_selection: query = query.filter(Trade.product_id == product_selection)
    if country_selection: query = query.filter(Trade.reporter == country_selection)
    if year: query = query.filter(Trade.year == year)

    query = query.order_by(Trade.value.desc())
    df = pd.read_sql_query(query.statement, session.bind)
    return df


# Filters
# ---------------------------------------------------------------------------
products = load_products()
countries = load_countries()

col1, col2, col3 = st.columns([1, 1, 2])

with col1:
    fuels_id = products[products["name"].str.contains("Fuels", case=False, na=False)]["id"].iloc[0]

    product_selection = st.selectbox(
        "Product:", 
        products["id"].unique().tolist(),
        index=products["id"].unique().tolist().index(fuels_id)
    )
with col2:
    country_options = [(name, iso3) for name, iso3 in zip(countries['name'], countries['iso_3'])]
    country_selection = st.selectbox("Country:", [name for name, _ in country_options])
    country_selection = next((iso3 for name, iso3 in country_options if name == country_selection), None)


trades = load_trades(product_selection, country_selection)
trades_timeseries = trades




with col3:
    year_options = trades["year"].unique()
    year_options = sorted(year_options, reverse=True)
    year_selection = st.selectbox("Year:", year_options)
    trades = trades[trades["year"] == year_selection ]

trades['value'] = round(trades['value'] / 1000, 2)
trades['weight'] = round((trades['value'] / trades['value'].sum()), 4) * 100


st.caption(f'{product_selection} / {country_selection} / {year_selection}')

# Layout
# ---------------------------------------------------------------------------
tab1, tab2 = st.tabs(["🌐 World Trade Map", "🔢 Raw Data"])

if trades.empty:
    st.warning(f"No trade data.")
    st.stop()

with tab1:
    trade_data = trades[['reporter_name', 'reporter_lng', 'reporter_lat', 'partner_name', 'partner_lng', 'value', 'weight', 'partner_lat', 'value' ]]
    trade_data['width'] = trade_data['weight'] / 8

    arc_layer = pdk.Layer(
        'ArcLayer',
        trade_data,
        get_source_position=['reporter_lng', 'reporter_lat'],
        get_target_position=['partner_lng', 'partner_lat'],
        get_width="width",
        get_height=0.2,
        get_tilt_slant=1,
        get_source_color=[100, 150, 255, 160],  # Blue start
        get_target_color=[50, 100, 255, 180],   # Blue end
        pickable=True
    )

    unique_coords = trades[['reporter_lat', 'reporter_lng']].drop_duplicates()

    center_lat = unique_coords['reporter_lat'].mean()
    center_lng = unique_coords['reporter_lng'].mean()

    view = pdk.ViewState(
        latitude=center_lat,
        longitude=center_lng,
        zoom=2.5,
        pitch=40
    )

    # Tooltip with country names and value
    deck = pdk.Deck(
        layers=[arc_layer],
        initial_view_state=view,
        map_style=None,
        tooltip={
            "html": """
            <b>{reporter_name}</b> → <b>{partner_name}</b><br/>
            Trade Value: ${value}B
            Trade Weight: ${weight}B

            """,
            "style": {"backgroundColor": "steelblue", "color": "white"}
        }
    )

    st.pydeck_chart(deck, width='stretch', height=600)


with tab2:
    tables = {
        'Trades': trades,
        'Product': products,
        'Countries': countries,
    }
    for table in tables:
        st.text(f'{table} | records ({len(tables[table])})')
        st.dataframe(tables[table], width='stretch')
        col1, col2, col3 = st.columns(3)
        st.divider()





# col1, col2 = st.columns([1, 1])
# with col1:
#     min_val = float(0)
#     max_val = float(trade_df["value"].max())

#     slider_range = st.slider(
#         "Select value range", min_value=min_val, max_value=max_val, value=(min_val, max_val)
#     )
#     min_slider, max_slider = slider_range
#     trade_df = trade_df[
#         (trade_df["value"] >= min_slider) & (trade_df["value"] <= max_slider)
#     ]


# with col2:
#     min_val = float(0)
#     max_val = float(trade_df["weight"].max())

#     slider_range = st.slider(
#         "Weight range", min_value=min_val, max_value=max_val, value=(min_val, max_val)
#     )
#     min_slider, max_slider = slider_range
#     trade_df = trade_df[
#         (trade_df["weight"] >= min_slider) & (trade_df["weight"] <= max_slider)
#     ]



# # Cytoscape
# # ----------------------------------------------------------------------

# trade_data = trade_df.to_dict("records")


# nodes = []
# edges = []

# partners = trade_df[["partner", "partner_name"]].copy()
# partners.columns = ["id", "name"]

# reporters = trade_df[["reporter", "reporter_name"]].copy()
# reporters.columns = ["id", "name"]

# country_df = pd.concat([partners, reporters], ignore_index=True)
# country_df = country_df.drop_duplicates()

# country_data = country_df.to_dict("records")
# country_list = [x["id"] for x in country_data]

# for x in country_data:
    
#     row = {
#         "data": {
#             "id": x["id"],
#             "label": x["name"] + f' ({x["id"]})',
#             "size": 20,  # Add size to node data
#         }
#     }
#     if row not in nodes:
#         nodes.append(row)

# for y in trade_data:
#     if y["reporter"] == y["partner"]:
#         continue

#     if y["reporter"] not in country_list:
#         continue

#     if y["partner"] not in country_list:
#         continue

#     edge_width = int(y["value"])
#     if edge_width > 1000:
#         edge_width = 10

#     row =         {
#             "data": {
#                 "id": f"{y['reporter']}-{y['partner']}",
#                 "source": y["reporter"],
#                 "target": y["partner"],
#                 "value": f"{y['weight']/100:.2%}",
#                 "width": y["weight"] / 10,  # Add width to edge data
#             }
#         }

#     if row not in edges:
#         edges.append(row)

# elements = nodes + edges

# # Updated stylesheet using data values
# stylesheet = [
#     {
#         "selector": "node",
#         "style": {
#             "label": "data(label)",
#             "background-color": "#4A90E2",
#             "color": "#fff",
#             "text-valign": "center",
#             "text-halign": "center",
#             "font-size": "14px",
#             "width": "data(size)",
#             "height": "data(size)",
#         },
#     },
#     {
#         "selector": "edge",
#         "style": {
#             "curve-style": "bezier",
#             "target-arrow-shape": "triangle",
#             "line-color": "#aaa",
#             "target-arrow-color": "#aaa",
#             "width": "data(width)",
#             "label": "data(value)",      # 👈 SHOW VALUE ON EDGE
#             "font-size": "12px",
#             "color": "#666",
#             "text-rotation": "autorotate",  # Follows edge curve
#             "text-margin-y": "-5px",       # Position above edge
#             "text-halign": "center",
#         },
#     },
#     {
#         "selector": ":selected",
#         "style": {
#             "background-color": "#4A90E2",
#             "line-color": "#2C598C",
#             "target-arrow-color": "#135AAC",
#             "label": "data(value)",  # Highlight selected
#             "color": "#000",
#             "font-weight": "bold",
#         },
#     },
# ]



# # Render the graph — layout IS supported here
# # breadthfirst, circle, grid, cose, random

# col1, col2 = st.columns([1, 1])



# with col1:
#     st.write("**Cytoscape Network Trade Map**")
#     options = ["cose", "breadthfirst", "circle", "grid", "random"]
#     layout = st.selectbox("Layout:", options)


#     selected = cytoscape(
#         elements,
#         stylesheet,
#     height="500px",
#         layout={
#             "name": layout,
#             "nodeRepulsion": 500000,
#         },
#         key="cytoscape",

#     )

# with col2:
#     st.write("**Map Projection Import Trade Value**")

#     graph_data = trade_df
#     graph_data = graph_data[['partner', 'partner_name', 'value']]

#     options = [ 'orthographic', 'equirectangular', 'mercator', 'conic equal area', 'azimuthal equal area', 'robinson', 'mollweide', 'hammer']
#     layout = st.selectbox("Projection", options)


#     fig = px.choropleth(
#         graph_data,
#         locations='partner',      # 👈 ISO3 column: 'ARE', 'BHR', etc.
#         color='value',       # Color intensity by trade volume
#         hover_name='partner_name',
#         color_continuous_scale='Blues',
#         projection=layout,  # World map projection
#         labels={'trade_value': 'Trade Volume'}
#     )
#     fig.update_layout(height=500, margin={"r":0,"t":40,"l":0,"b":0})
#     st.plotly_chart(fig, width='stretch')



# col1, col2 = st.columns([1, 1])

# with col1:

#     timeseries_trade_df['trade'] = (
#         timeseries_trade_df['reporter'] + ' > ' +  timeseries_trade_df['partner_name']
#     )
#     timeseries_trade_df = timeseries_trade_df[['trade', 'value', 'period', 'reporter', 'partner']]
#     timeseries_trade_df = timeseries_trade_df.dropna()


#     countries_to_filter = trade_df['partner'].to_list()
#     timeseries_trade_df = timeseries_trade_df[timeseries_trade_df["partner"].isin(countries_to_filter)]

#     countries_to_filter = trade_df['reporter'].to_list()
#     timeseries_trade_df = timeseries_trade_df[timeseries_trade_df["reporter"].isin(countries_to_filter)]


#     chart = (alt.Chart(timeseries_trade_df)
#         .mark_line(strokeWidth=3)
#         .encode(
#             x=alt.X('period:Q', title='Period'),
#             y=alt.Y('value:Q', title='Trade Value'),
#             color=alt.Color('trade:N', title='Trade Flow'),
#             strokeDash=alt.StrokeDash('trade:N')
#         )
#         .properties(
#             title='Trade Flow over time',
#             height=500
#         )
#         .interactive()
#     )

#     chart






# with col2:
#     graph_data = trade_df

#     graph_data['trade'] = (
#         trade_df['reporter'] + ' > ' +  trade_df['partner_name']
#     )
#     graph_data = graph_data[['trade', 'value']]
#     graph_data = graph_data.sort_values('value', ascending=False).head(20)  # Top 20 for readability
#     graph_data['value_mil'] = graph_data['value'] / 1_000_000

#     chart = (
#         alt.Chart(graph_data)
#         .mark_bar(color='steelblue')
#         .encode(
#             x=alt.X('value_mil:Q', 
#                     title='Trade Value (Mil USD)',
#                     axis=alt.Axis(format='.1f')),  # 1 decimal, e.g., 1.2M
#             y=alt.Y('trade:N', sort=None, title='Trade Flow'),
#             tooltip=[alt.Tooltip('trade:N'), alt.Tooltip('value:Q', format='.3s')]  # Full value on hover
#         )
#         .properties(height=500, title='Top Trade Flows (in Millions)')
#     )

#     st.altair_chart(chart, width='stretch')

# st.divider()


# example_data = {
#     'reporter_iso3': ['World'] * 12,
#     'partner_name': ['USA', 'China', 'India', 'Germany', 'Japan', 'UK', 'France', 'Italy', 'South Korea', 'UAE', 'Saudi Arabia', 'Iran'],
#     'partner_iso3': ['USA', 'CHN', 'IND', 'DEU', 'JPN', 'GBR', 'FRA', 'ITA', 'KOR', 'ARE', 'SAU', 'IRN'],
#     'continent': ['North America', 'Asia', 'Asia', 'Europe', 'Asia', 'Europe', 'Europe', 'Europe', 'Asia', 'Asia', 'Asia', 'Asia'],
#     'value': np.random.uniform(50, 500, 12),  # $M trade volume
#     'weight': np.random.uniform(0.02, 0.15, 12),
#     'period': 2024
# }
# df = pd.DataFrame(example_data)
# df['weight'] = df['weight'] / df['weight'].sum()  # Normalize to 1.0

# st.dataframe(df, width='stretch')
# fig = px.treemap(
#     df,
#     path=[px.Constant('World'), 'continent', 'partner_name'],
#     values='weight',
#     color='value',
#     hover_data=['partner_iso3', 'value', 'weight'],
#     color_continuous_scale='Blues',
#     color_continuous_midpoint=np.median(df['value'])
# )

# fig.update_traces(root_color="#4682B4")  # SteelBlue
# fig.update_layout(height=500)
# st.plotly_chart(fig, width='stretch')

