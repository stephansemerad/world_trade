import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text
from st_cytoscape import cytoscape
import altair as alt
import numpy as np
import plotly.express as px


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
        SELECT
        REPORTER, 
        r_country.name as REPORTER_name, 
        PARTNER, 
        p_country.name as PARTNER_name, 

        value, period, PRODUCTCODE FROM trade
        left join countries as r_country on r_country.id == REPORTER
        left join countries as p_country on p_country.id == PARTNER

                where 1 = 1

                 and REPORTER not in 
                 ('WLD', '999', 'UNS', 'MEA', 'SSF', 'EAS')
                 and PARTNER not in 
                 ('WLD', '999', 'UNS', 'MEA', 'SSF', 'EAS', 'ECS', 'OAS', 'LCN', 'SAS')

                 order by value desc

        """
    )
    with engine.connect() as conn:
        return pd.read_sql_query(query, conn)


trade_df = load_trades()
timeseries_trade_df = trade_df

trade_df = trade_df.drop_duplicates()
trade_df.columns = trade_df.columns.str.lower()

timeseries_trade_df = timeseries_trade_df.drop_duplicates()
timeseries_trade_df.columns = timeseries_trade_df.columns.str.lower()


if trade_df.empty:
    st.warning(f"No trade data.")
    st.stop()


col1, col2, col3, col4, col5 = st.columns([1, 1, 2, 2, 2])

with col1:
    options = ["cose", "breadthfirst", "circle", "grid", "random"]
    layout = st.selectbox("Choose:", options)

with col2:
    year_options = trade_df["period"].unique()
    year_options = sorted(year_options, reverse=True)
    year_selection = st.selectbox("Select Year:", year_options)
    if year_selection:
        trade_df = trade_df[trade_df["period"] == year_selection ]


with col3:
    product_options = trade_df["productcode"].unique().tolist()
    product_selection = st.selectbox("Select Product:", product_options)

with col4:
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
        timeseries_trade_df = trade_df[trade_df["reporter_name"].isin(exporting_country)]

with col5:
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
        timeseries_trade_df = trade_df[trade_df["partner_name"].isin(importing_country)]


min_val = float(0)
max_val = float(trade_df["value"].max())

slider_range = st.slider(
    "Select value range", min_value=min_val, max_value=max_val, value=(min_val, max_val)
)
min_slider, max_slider = slider_range
trade_df = trade_df[
    (trade_df["value"] >= min_slider) & (trade_df["value"] <= max_slider)
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
                "width": 1,  # Add width to edge data
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
        },
    },
    {
        "selector": ":selected",
        "style": {
            "background-color": "#E94F37",
            "line-color": "#E94F37",
            "target-arrow-color": "#E94F37",
        },
    },
]


# Render the graph — layout IS supported here
# breadthfirst, circle, grid, cose, random

col1, col2 = st.columns([2, 1])

with col1:
    selected = cytoscape(
        elements,
        stylesheet,
    height="500px",  # 👈 STRING with "px" - not int!
        layout={
            "name": layout,
            "nodeRepulsion": 400000,  # higher = nodes push apart more
        },
        key="cytoscape",

    )


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

    st.altair_chart(chart, use_container_width=True)


col1, col2 = st.columns([2, 1])

with col1:

    graph_data = timeseries_trade_df
    graph_data['trade'] = (
        graph_data['reporter'] + ' > ' +  graph_data['partner_name']
    )
    graph_data = graph_data[['trade', 'value', 'period']]
    graph_data = graph_data.dropna()
    
    chart = (alt.Chart(graph_data)
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
    graph_data = graph_data[['partner', 'partner_name', 'value']]

    fig = px.choropleth(
        graph_data,
        locations='partner',      # 👈 ISO3 column: 'ARE', 'BHR', etc.
        color='value',       # Color intensity by trade volume
        hover_name='partner_name',
        color_continuous_scale='Blues',
        projection='natural earth',  # World map projection
        title="World Trade Map",
        labels={'trade_value': 'Trade Volume'}
    )

    fig.update_layout(height=600, margin={"r":0,"t":40,"l":0,"b":0})
    st.plotly_chart(fig, use_container_width=True)


st.dataframe(trade_df, width="stretch")
st.dataframe(timeseries_trade_df, width="stretch")
