import math
import pandas as pd
import polars as pl
import streamlit as st
from sqlalchemy import create_engine, text
import pycountry
from st_cytoscape import cytoscape


# ── page config ───────────────────────────────────────────────────────── #

st.set_page_config(
    page_title="World Trade Explorer",
    page_icon="🌐",
    layout="wide",
)

DB_PATH = "sqlite:///trade.db"

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

                where period = 2020

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
trade_df.columns = trade_df.columns.str.lower()
trade_data = trade_df.to_dict("records")

if trade_df.empty:
    st.warning(f"No trade data.")
    st.stop()


# ── load & filter data ────────────────────────────────────────────────── #


st.title("🔵 Cytoscape.js in Streamlit")
st.write("A simple interactive graph example.")

col1, col2, col3 = st.columns([1, 2, 1])  # Adjust ratios as needed

with col1:
    options = ["cose", "breadthfirst", "circle", "grid", "random"]
    layout = st.selectbox("Choose:", options)


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

    edges.append(
        {
            "data": {
                "id": f"{y['reporter']}-{y['partner']}",
                "source": y["reporter"],
                "target": y["partner"],
                "width": 1,  # Add width to edge data
            }
        }
    )

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

selected = cytoscape(
    elements,
    stylesheet,
    layout={
        "name": layout,
        "nodeRepulsion": 400000,  # higher = nodes push apart more
    },
    height="500px",
    key="cytoscape123",
)


if selected["nodes"]:
    node = selected["nodes"][0]  # First selected node
    st.write(f"**ID**: `{node}`")
    # st.write(f"**Label**: {node['data']['label']}")
    # st.write(f"**Size**: {node['data'].get('size', 'N/A'):.1f}px")

    # # Show trade totals (from your node_values calculation)
    # total_trade = nodes.get(node["data"]["id"], 0)
    # st.metric("Total Trade Volume", f"{total_trade:.3f}")

    # # Show connected partners
    # partners = [
    #     e["data"]["target"]
    #     for e in selected["edges"]
    #     if e["data"]["source"] == node["data"]["id"]
    # ]
    # partners += [
    #     e["data"]["source"]
    #     for e in selected["edges"]
    #     if e["data"]["target"] == node["data"]["id"]
    # ]
    # if partners:
    #     st.write("**Partners**:", ", ".join(set(partners)))
else:
    st.info("👆 Click a node to see details")

st.dataframe(trade_df, width="stretch")
