import pandas as pd 


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
            "line-color": "#aaa",
            "target-arrow-color": "#aaa",
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


    trades =  trades.drop_duplicates()
    trades = trades[trades['weight'] > 0]

    reporters = trades[["reporter", "reporter_name"]].copy()
    partners = trades[["partner", "partner_name"]].copy()

    reporters.columns = ["id", "name"]
    partners.columns = ["id", "name"]

    country_df = pd.concat([partners, reporters], ignore_index=True).drop_duplicates().to_dict("records")

    country_data = country_df
    country_list = [x["id"] for x in country_data]



    for x in country_data:
        if x['id'] == None or x['id'] == '':
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
    return elements

