import pandas as pd
import plotly.express as px
import streamlit as st


def make_globe(trades, export_type="importer"):
    graph_data = trades
    graph_data = (
        graph_data.groupby([f"{export_type}", f"{export_type}_name"])["value"]
        .sum()
        .reset_index()
    )

    options = [
        "orthographic",
        "equirectangular",
        "mercator",
        "conic equal area",
        "azimuthal equal area",
        "robinson",
        "mollweide",
        "hammer",
    ]
    layout = st.selectbox("Projection", options, key=f"layout_{export_type}")

    fig = px.choropleth(
        graph_data,
        locations=f"{export_type}",  # 👈 ISO3 column: 'ARE', 'BHR', etc.
        color="value",  # Color intensity by trade volume
        hover_name=f"{export_type}_name",
        color_continuous_scale="Blues",
        projection=layout,  # World map projection
        labels={"value": "Trade Volume"},
    )

    fig.update_layout(height=600, margin={"r": 0, "t": 40, "l": 0, "b": 0})
    st.plotly_chart(fig, width="stretch")


cytoscape_stylesheet = [
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
            "line-color": "#555",
            "target-arrow-color": "#555",
            "width": "data(width)",
            "label": "data(value)",
            "font-size": "12px",
            "color": "#666",
            "text-rotation": "autorotate",
            "text-margin-y": "-5px",
            "text-halign": "center",
        },
    },
    {
        "selector": ":selected",
        "style": {
            "background-color": "#4A90E2",
            "line-color": "#2C598C",
            "target-arrow-color": "#135AAC",
            "label": "data(value)",
            "color": "#000",
            "font-weight": "bold",
        },
    },
]


def cytoscape_convert_to_nodes_and_edges(trades):
    nodes = []
    edges = []

    trades = trades.drop_duplicates()
    trades = trades[trades["weight"] > 0]

    exporters = trades[["exporter", "exporter_name"]].copy()
    importer = trades[["importer", "importer_name"]].copy()

    exporters.columns = ["id", "name"]
    importer.columns = ["id", "name"]

    country_df = (
        pd.concat([importer, exporters], ignore_index=True)
        .drop_duplicates()
        .to_dict("records")
    )

    country_data = country_df
    country_list = [x["id"] for x in country_data]

    for x in country_data:
        if x["id"] == None or x["id"] == "":
            continue

        row = {
            "data": {
                "id": x["id"],
                "label": x["name"] + f' ({x["id"]})',
                "size": 20,
            }
        }
        if row not in nodes:
            nodes.append(row)

    for y in trades.drop_duplicates().to_dict("records"):
        if y["exporter"] == y["importer"]:
            continue

        if y["exporter"] not in country_list:
            continue

        if y["importer"] not in country_list:
            continue

        edge_width = int(y["value"])
        if edge_width > 1000:
            edge_width = 10

        row = {
            "data": {
                "id": f"{y['exporter']}-{y['importer']}",
                "source": y["exporter"],
                "target": y["importer"],
                "value": f"{y['weight']/100:.2%}",
                "width": y["weight"],  # Add width to edge data
            }
        }

        if row not in edges:
            edges.append(row)

    elements = nodes + edges
    return elements
