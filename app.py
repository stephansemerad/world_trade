import pandas as pd
import streamlit as st
from st_cytoscape import cytoscape
import altair as alt
import numpy as np
import plotly.express as px
import pydeck as pdk
from model import SessionLocal, Country, Product, Trade, API_status
from sqlalchemy.orm import aliased
from utils import cytoscape_stylesheet, cytoscape_convert_to_nodes_and_edges

session = SessionLocal()

st.set_page_config(page_title="World Trade Map", page_icon="🌐", layout="wide")
st.title("🌐 World Trade Map")
st.write("A simple interactive graph example.")

# @st.cache_data
def load_countries():
    trade_reported_subquery = session.query(Trade.reporter.distinct()).filter(Trade.value > 0).subquery()
    query = (
        session.query(Country)
        .filter(Country.iso_3.in_(trade_reported_subquery))
        .order_by(Country.name.desc())
    )
    df = pd.read_sql_query(query.statement, session.bind)
    return df

def load_products():
    query = (
        session.query(Product)
        .filter(Product.id.in_(session.query(Trade.product_id.distinct())))
        .order_by(Product.id.desc())
    )
    df = pd.read_sql_query(query.statement, session.bind)
    return df



def load_trades(product_selection=None, mode_of_transport_selection='TOTAL MOT',  country_selection=[], year=None):
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
        .join(partner_country, partner_country.iso_3 == Trade.partner)
        .filter(Trade.value != None)  # Exclude records with null value
        .filter(Trade.value > 0)  # Exclude records with zero or negative value
        .filter(Trade.reporter != "") # Exclude records with empty reporter
        .filter(Trade.partner != "") # Exclude records with empty partner
    )

    if product_selection: 
        query = query.filter(Trade.product_id == product_selection)

    if mode_of_transport_selection: 
        query = query.filter(Trade.mode_of_transport == mode_of_transport_selection)

    if country_selection: 
        query = query.filter(Trade.reporter.in_(country_selection))

    if year: 
        query = query.filter(Trade.year == year)

    query = query.order_by(Trade.value.desc())
    df = pd.read_sql_query(query.statement, session.bind)
    return df




# Filters
# ---------------------------------------------------------------------------
products = load_products()
countries = load_countries()

col1, col2, col3, col4 = st.columns([1, 1, 1, 1])

with col1:
    product_selection = st.selectbox(
        "Product:", 
        products["id"].unique().tolist(),
    )


with col2:
    country_options = [(name, iso3) for name, iso3 in zip(countries['name'], countries['iso_3'])]

    # Multi-select on country names
    country_selected_names = st.multiselect(
        "Country:",
        options=[name for name, _ in country_options]
    )

    # Convert selected names to iso3 list
    country_selection = [iso3 for name, iso3 in country_options if name in country_selected_names]

mode_of_transport_selection = 'TOTAL MOT'

trades = load_trades(product_selection, mode_of_transport_selection, country_selection)

trades_timeseries = trades

with col3:
    year_options = trades["year"].unique()
    year_options = sorted(year_options, reverse=True)
    year_selection = st.selectbox("Year:", year_options)
    trades = trades[trades["year"] == year_selection ]



with col4:
    weight_selection = st.selectbox("Weight", ['Global', 'Country'])
    if weight_selection == 'Global':
        try:
            trades['weight'] = round((trades['value'] / trades['value'].sum())* 100, 2) 
        except Exception as e:
            print(e)
            trades['weight'] = 0

    if weight_selection == 'Country':
        trades['weight'] = (
            trades['value']
            .div(trades.groupby('reporter')['value'].transform('sum'))
            .mul(100)
            .round(2)
        )


st.caption(f'{product_selection} / {', '.join(country_selected_names)} / {year_selection}')

# Layout
# ---------------------------------------------------------------------------
tab1, tab2, tab3, tabx = st.tabs(["🌐 World Trade Map", "Graph", "Exporters / Importers", "🔢 Raw Data"])

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
        pitch=25
    )

    # Tooltip with country names and value
    deck = pdk.Deck(
        layers=[arc_layer],
        initial_view_state=view,
        map_style=None,
        tooltip={
            "html": """
            <b>{reporter_name}</b> → <b>{partner_name}</b><br/>
            Trade Value: ${value}B<br/>
            Trade Weight: ${weight}%
            """,
            "style": {"backgroundColor": "steelblue", "color": "white"}
        }
    )

    st.pydeck_chart(deck, width='stretch', height=600)

with tab2:
    # Cytoscape
    # ----------------------------------------------------------------------
    # Render the graph — layout IS supported here
    # breadthfirst, circle, grid, cose, random
    st.write("**Cytoscape Network Trade Map**")
    options = ["cose", "breadthfirst", "circle", "grid", "random"]
    layout = st.selectbox("Layout:", options)

    cytoscape(
        cytoscape_convert_to_nodes_and_edges(trades),
        cytoscape_stylesheet,
        height="500px",
        layout={
            "name": layout,
            "nodeRepulsion": 500000,
        },
        key="cytoscape",
    )


with tab3:
    col1, col2 = st.columns([1, 1])
    with col1:
        st.write("**Top Exporters**")
        # Export flows: what reporter sends to which partners
        exports = (
            trades.
            groupby(["product_id", "year", "reporter", "reporter_name"])
            .agg({"value": "sum", "weight": "sum"})
            .reset_index()
            .sort_values("value", ascending=False)
            .head(10)
        )
        exports["trade_type"] = "export"

        st.dataframe(exports, width='stretch')

    with col2:
        st.write("**Top Importers**")
        # Import flows: what partner receives from which reporters
        imports = (
            trades.
            groupby(["product_id", "year", "partner", "partner_name"])
            .agg({"value": "sum", "weight": "sum"})
            .reset_index()
            .sort_values("value", ascending=False)
            .head(10)
        )
        imports["trade_type"] = "import"
        st.dataframe(imports, width='stretch')







with tabx:
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

