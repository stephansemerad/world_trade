import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text
from st_cytoscape import cytoscape
import altair as alt
import numpy as np
import plotly.express as px
import pydeck as pdk


# ── page config ───────────────────────────────────────────────────────── #

st.set_page_config(
    page_title="World Trade Explorer",
    page_icon="🌐",
    layout="wide",
)

DB_PATH = "sqlite:///trade.db"

# Dropdown and Selectors
# -----------------------------------------------------------------------
st.title("🌐 World Trade Map")
st.write("A simple interactive graph example.")


# ── data loading ──────────────────────────────────────────────────────── #
@st.cache_resource
def get_engine():
    return create_engine(DB_PATH)

@st.cache_data
def load_products() -> pd.DataFrame:
    engine = get_engine()
    return pd.read_sql("SELECT id, name FROM products", engine)

@st.cache_data
def load_trades() -> pd.DataFrame:
    engine = get_engine()
    query = text(
        """
        SELECT DISTINCT
        REPORTER, 
        r_country.name as REPORTER_name, 
        PARTNER, 
        p_country.name as PARTNER_name, 

        value, period, PRODUCTCODE FROM trade
        left join countries as r_country on r_country.id == REPORTER
        left join countries as p_country on p_country.id == PARTNER
        where 1 = 1
        order by value desc

        """
    )
    with engine.connect() as conn:
        return pd.read_sql_query(query, conn)


trade_df = load_trades()

trade_df = trade_df.drop_duplicates()
trade_df.columns = trade_df.columns.str.lower()

trade_df = trade_df[~trade_df['partner'].isin(['SAS', 'ECS', 'LCN', 'NAC', 'OAS', 'FRE', 'WLD', '999', 'UNS', 'MEA', 'SSF', 'EAS'])]


trade_df['weight'] = trade_df.groupby(['reporter', 'period'])['value'].transform(
    lambda x: (x / x.sum()).round(4) * 100
)


timeseries_trade_df = load_trades()
timeseries_trade_df = timeseries_trade_df.drop_duplicates()
timeseries_trade_df.columns = timeseries_trade_df.columns.str.lower()

trade_df = trade_df[trade_df['weight'] > 0]

if trade_df.empty:
    st.warning(f"No trade data.")
    st.stop()


col1, col2, col3, col4 = st.columns([1, 1, 2, 2])


with col1:

    year_options = trade_df["period"].unique()
    year_options = sorted(year_options, reverse=True)
    year_selection = st.selectbox("Select Year:", year_options)
    if year_selection:
        trade_df = trade_df[trade_df["period"] == year_selection ]


with col2:
    product_options = trade_df["productcode"].unique().tolist()
    product_selection = st.selectbox("Select Product:", product_options)

with col3:
    exporting_countries_df = trade_df[["reporter", "reporter_name"]]
    exporting_countries = dict(
        zip(exporting_countries_df["reporter_name"], exporting_countries_df["reporter"])
    )
    exporting_country = st.multiselect(
        "Exporting Country",
        options=list(exporting_countries.keys()),
    )
    if exporting_country:
        trade_df = trade_df[trade_df["reporter_name"].isin(exporting_country)]
        timeseries_trade_df = timeseries_trade_df[timeseries_trade_df["reporter_name"].isin(exporting_country)]

with col4:
    importing_countries_df = trade_df[["partner", "partner_name"]]
    importing_countries = dict(
        zip(importing_countries_df["partner_name"], importing_countries_df["partner"])
    )
    importing_country = st.multiselect(
        "Importing Country",
        options=list(importing_countries.keys()),
    )
    if importing_country:
        trade_df = trade_df[trade_df["partner_name"].isin(importing_country)]
        timeseries_trade_df = timeseries_trade_df[timeseries_trade_df["partner_name"].isin(importing_country)]










col1, col2 = st.columns([1, 1])
with col1:
    min_val = float(0)
    max_val = float(trade_df["value"].max())

    slider_range = st.slider(
        "Select value range", min_value=min_val, max_value=max_val, value=(min_val, max_val)
    )
    min_slider, max_slider = slider_range
    trade_df = trade_df[
        (trade_df["value"] >= min_slider) & (trade_df["value"] <= max_slider)
    ]


with col2:
    min_val = float(0)
    max_val = float(trade_df["weight"].max())

    slider_range = st.slider(
        "Weight range", min_value=min_val, max_value=max_val, value=(min_val, max_val)
    )
    min_slider, max_slider = slider_range
    trade_df = trade_df[
        (trade_df["weight"] >= min_slider) & (trade_df["weight"] <= max_slider)
    ]



# Cytoscape
# ----------------------------------------------------------------------

trade_data = trade_df.to_dict("records")


nodes = []
edges = []

partners = trade_df[["partner", "partner_name"]].copy()
partners.columns = ["id", "name"]

reporters = trade_df[["reporter", "reporter_name"]].copy()
reporters.columns = ["id", "name"]

country_df = pd.concat([partners, reporters], ignore_index=True)
country_df = country_df.drop_duplicates()

country_data = country_df.to_dict("records")
country_list = [x["id"] for x in country_data]

for x in country_data:
    
    row = {
        "data": {
            "id": x["id"],
            "label": x["name"] + f' ({x["id"]})',
            "size": 20,  # Add size to node data
        }
    }
    if row not in nodes:
        nodes.append(row)

for y in trade_data:
    if y["reporter"] == y["partner"]:
        continue

    if y["reporter"] not in country_list:
        continue

    if y["partner"] not in country_list:
        continue

    edge_width = int(y["value"])
    if edge_width > 1000:
        edge_width = 10

    row =         {
            "data": {
                "id": f"{y['reporter']}-{y['partner']}",
                "source": y["reporter"],
                "target": y["partner"],
                "value": f"{y['weight']/100:.2%}",
                "width": y["weight"] / 10,  # Add width to edge data
            }
        }

    if row not in edges:
        edges.append(row)

elements = nodes + edges

# Updated stylesheet using data values
stylesheet = [
    {
        "selector": "node",
        "style": {
            "label": "data(label)",
            "background-color": "#4A90E2",
            "color": "#fff",
            "text-valign": "center",
            "text-halign": "center",
            "font-size": "14px",
            "width": "data(size)",
            "height": "data(size)",
        },
    },
    {
        "selector": "edge",
        "style": {
            "curve-style": "bezier",
            "target-arrow-shape": "triangle",
            "line-color": "#aaa",
            "target-arrow-color": "#aaa",
            "width": "data(width)",
            "label": "data(value)",      # 👈 SHOW VALUE ON EDGE
            "font-size": "12px",
            "color": "#666",
            "text-rotation": "autorotate",  # Follows edge curve
            "text-margin-y": "-5px",       # Position above edge
            "text-halign": "center",
        },
    },
    {
        "selector": ":selected",
        "style": {
            "background-color": "#4A90E2",
            "line-color": "#2C598C",
            "target-arrow-color": "#135AAC",
            "label": "data(value)",  # Highlight selected
            "color": "#000",
            "font-weight": "bold",
        },
    },
]



# Render the graph — layout IS supported here
# breadthfirst, circle, grid, cose, random


trade_dict = {
    'country0': ['USA', 'UK'],
    'lon0': [-74.00, -0.13],
    'lat0': [40.71, 51.51],
    'country1': ['UK', 'China'],
    'lon1': [-0.13, 116.40],
    'lat1': [51.51, 39.90],
    'value': [100, 200]  # e.g., billions USD
}
trade_data = pd.DataFrame(trade_dict)

# Blue ArcLayer
arc_layer = pdk.Layer(
    'ArcLayer',
    trade_data,
    get_source_position=['lon0', 'lat0'],
    get_target_position=['lon1', 'lat1'],
    get_width="value / 10",
    get_height=0.6,
    get_tilt_slant=15,
    get_source_color=[100, 150, 255, 160],  # Blue start
    get_target_color=[50, 100, 255, 180],   # Blue end
    pickable=True
)

view = pdk.ViewState(latitude=20, longitude=0, zoom=1.4, pitch=40)

# Tooltip with country names and value
deck = pdk.Deck(
    layers=[arc_layer],
    initial_view_state=view,
    map_style=None,
    tooltip={
        "html": """
        <b>{country0}</b> → <b>{country1}</b><br/>
        Trade Value: ${value}B
        """,
        "style": {"backgroundColor": "steelblue", "color": "white"}
    }
)

st.pydeck_chart(deck, width='stretch', height=200)

col1, col2 = st.columns([1, 1])



with col1:
    st.write("**Cytoscape Network Trade Map**")
    options = ["cose", "breadthfirst", "circle", "grid", "random"]
    layout = st.selectbox("Layout:", options)


    selected = cytoscape(
        elements,
        stylesheet,
    height="500px",
        layout={
            "name": layout,
            "nodeRepulsion": 500000,
        },
        key="cytoscape",

    )

with col2:
    st.write("**Map Projection Import Trade Value**")

    graph_data = trade_df
    graph_data = graph_data[['partner', 'partner_name', 'value']]

    options = [ 'orthographic', 'equirectangular', 'mercator', 'conic equal area', 'azimuthal equal area', 'robinson', 'mollweide', 'hammer']
    layout = st.selectbox("Projection", options)


    fig = px.choropleth(
        graph_data,
        locations='partner',      # 👈 ISO3 column: 'ARE', 'BHR', etc.
        color='value',       # Color intensity by trade volume
        hover_name='partner_name',
        color_continuous_scale='Blues',
        projection=layout,  # World map projection
        labels={'trade_value': 'Trade Volume'}
    )
    fig.update_layout(height=500, margin={"r":0,"t":40,"l":0,"b":0})
    st.plotly_chart(fig, width='stretch')



col1, col2 = st.columns([1, 1])

with col1:

    timeseries_trade_df['trade'] = (
        timeseries_trade_df['reporter'] + ' > ' +  timeseries_trade_df['partner_name']
    )
    timeseries_trade_df = timeseries_trade_df[['trade', 'value', 'period', 'reporter', 'partner']]
    timeseries_trade_df = timeseries_trade_df.dropna()


    countries_to_filter = trade_df['partner'].to_list()
    timeseries_trade_df = timeseries_trade_df[timeseries_trade_df["partner"].isin(countries_to_filter)]

    countries_to_filter = trade_df['reporter'].to_list()
    timeseries_trade_df = timeseries_trade_df[timeseries_trade_df["reporter"].isin(countries_to_filter)]


    chart = (alt.Chart(timeseries_trade_df)
        .mark_line(strokeWidth=3)
        .encode(
            x=alt.X('period:Q', title='Period'),
            y=alt.Y('value:Q', title='Trade Value'),
            color=alt.Color('trade:N', title='Trade Flow'),
            strokeDash=alt.StrokeDash('trade:N')
        )
        .properties(
            title='Trade Flow over time',
            height=500
        )
        .interactive()
    )

    chart






with col2:
    graph_data = trade_df

    graph_data['trade'] = (
        trade_df['reporter'] + ' > ' +  trade_df['partner_name']
    )
    graph_data = graph_data[['trade', 'value']]
    graph_data = graph_data.sort_values('value', ascending=False).head(20)  # Top 20 for readability
    graph_data['value_mil'] = graph_data['value'] / 1_000_000

    chart = (
        alt.Chart(graph_data)
        .mark_bar(color='steelblue')
        .encode(
            x=alt.X('value_mil:Q', 
                    title='Trade Value (Mil USD)',
                    axis=alt.Axis(format='.1f')),  # 1 decimal, e.g., 1.2M
            y=alt.Y('trade:N', sort=None, title='Trade Flow'),
            tooltip=[alt.Tooltip('trade:N'), alt.Tooltip('value:Q', format='.3s')]  # Full value on hover
        )
        .properties(height=500, title='Top Trade Flows (in Millions)')
    )

    st.altair_chart(chart, width='stretch')

st.divider()


example_data = {
    'reporter_iso3': ['World'] * 12,
    'partner_name': ['USA', 'China', 'India', 'Germany', 'Japan', 'UK', 'France', 'Italy', 'South Korea', 'UAE', 'Saudi Arabia', 'Iran'],
    'partner_iso3': ['USA', 'CHN', 'IND', 'DEU', 'JPN', 'GBR', 'FRA', 'ITA', 'KOR', 'ARE', 'SAU', 'IRN'],
    'continent': ['North America', 'Asia', 'Asia', 'Europe', 'Asia', 'Europe', 'Europe', 'Europe', 'Asia', 'Asia', 'Asia', 'Asia'],
    'value': np.random.uniform(50, 500, 12),  # $M trade volume
    'weight': np.random.uniform(0.02, 0.15, 12),
    'period': 2024
}
df = pd.DataFrame(example_data)
df['weight'] = df['weight'] / df['weight'].sum()  # Normalize to 1.0

st.dataframe(df, width='stretch')
fig = px.treemap(
    df,
    path=[px.Constant('World'), 'continent', 'partner_name'],
    values='weight',
    color='value',
    hover_data=['partner_iso3', 'value', 'weight'],
    color_continuous_scale='Blues',
    color_continuous_midpoint=np.median(df['value'])
)

fig.update_traces(root_color="#4682B4")  # SteelBlue
fig.update_layout(height=500)
st.plotly_chart(fig, width='stretch')

