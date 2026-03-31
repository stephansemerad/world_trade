import pandas as pd
import streamlit as st
from st_cytoscape import cytoscape
import altair as alt
import numpy as np
import plotly.express as px
import pydeck as pdk
from model import SessionLocal, Country, Product, Trade, Population
from sqlalchemy.orm import aliased
from utils import cytoscape_stylesheet, cytoscape_convert_to_nodes_and_edges
from utils import make_globe


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

def load_population(country_selection=[]):
    trade_reported_subquery = session.query(Trade.reporter.distinct()).filter(Trade.value > 0).subquery()

    query = (
        session.query(Population, Country.name, Country.continent_name)
        .join(Country, Country.iso_3 == Population.country_code)
        .filter(Population.country_code.in_(trade_reported_subquery))
        .filter(Population.value != None)
        .filter(Population.value > 0)
        
    )

    if country_selection: 
        query = query.filter(Population.country_code.in_(country_selection))

    query = query.order_by(Population.value.desc())
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
population = load_population(country_selection)


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

slider_range = st.slider("Weight Range", min_value=float(0), max_value=float(100), value=(float(0), float(100)))
min_slider, max_slider = slider_range
trades = trades[(trades["weight"] >= min_slider) & (trades["weight"] <= max_slider)]

st.caption(f'{product_selection} / {', '.join(country_selected_names)} / {year_selection}')

# Layout
# ---------------------------------------------------------------------------

tab1, tab2, tab3, tab4, tabx = st.tabs(
    [
        "🌐 World Trade Map", # 1
        "Graph", # 2
        "Exporters / Importers", # 3
        "Population", # 4
        "🔢 Raw Data" # 5
    ],
     on_change="rerun"
)

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

    st.dataframe(trades)

with tab2:

    col1, col2 = st.columns([1, 1])

    options = ["cose", "breadthfirst", "circle", "grid", "random"]
    layout = st.selectbox("Layout:", options)



    with col1:
        # Cytoscape
        # ----------------------------------------------------------------------
        # Render the graph — layout IS supported here
        # breadthfirst, circle, grid, cose, random
        st.write("**Cytoscape Network Trade Map**")

        cytoscape(
            cytoscape_convert_to_nodes_and_edges(trades),
            cytoscape_stylesheet,
            height="600px",
            layout={
                "name": layout,
                "nodeRepulsion": 600000,
            },
            key="cytoscape",
        )

    with col2:
        graph_data = trades

        graph_data['trade'] = (
            trades['reporter'] + ' > ' +  trades['partner_name']
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
                        axis=alt.Axis(format='.1f'),
                        scale=alt.Scale(padding=0.4)  # CORRECT: scale padding (0-1), not axis
                        ),  # 1 decimal, e.g., 1.2M
                y=alt.Y('trade:N', sort=None, title='Trade Flow'),
                tooltip=[alt.Tooltip('trade:N'), alt.Tooltip('value:Q', format='.3s')]  # Full value on hover
            )
            .properties(height=600, title='Top Trade Flows (in Millions)')
        )

        st.altair_chart(chart, width='stretch')

    st.divider()

with tab3:
    col1, col2 = st.columns([1, 1])
    with col1:
        st.write("**Top Exporters**")
        # Export flows: what reporter sends to which partners
        exports = (
            trades.
            groupby(["product_id", "year", "reporter", "reporter_name"])
            .agg({"value": "sum", "weight": "sum"})
            .sort_values("value", ascending=False)
            .reset_index()
        )

        graph_data = exports
        graph_data = (
            graph_data[['reporter_name', 'value']]
            .sort_values('value', ascending=False)
            .head(20)
        )
        graph_data['value_mil'] = graph_data['value'] / 1_000_000

        chart = (
            alt.Chart(graph_data)
            .mark_bar(color='steelblue')
            .encode(
                x=alt.X('value_mil:Q', 
                        title='Trade Value (Mil USD)',
                        axis=alt.Axis(format='.1f')),  # 1 decimal, e.g., 1.2M
                y=alt.Y('reporter_name:N', sort=None, title='Reporter'),
                tooltip=[alt.Tooltip('reporter_name:N'), alt.Tooltip('value:Q', format='.3s')]  # Full value on hover
            )
            .properties(height=500, title='Top Trade Flows (in Millions)')
        )

        st.altair_chart(chart, width='stretch')

        make_globe(trades, export_type='reporter')

        # exports['value'] = exports['value'].map('${:,.2f}'.format)
        # exports['weight'] = exports['weight'].map('{:,.2f}'.format)
        # exports["trade_type"] = "export"
        # st.dataframe(exports, width='stretch')

    with col2:
        st.write("**Top Importers**")
        # Import flows: what partner receives from which reporters
        imports = (
            trades.
            groupby(["product_id", "year", "partner", "partner_name"])
            .agg({"value": "sum", "weight": "sum"})
            .sort_values("value", ascending=False)
            .reset_index()
        )

        graph_data = imports
        graph_data = (
            graph_data[['partner_name', 'value']]
            .sort_values('value', ascending=False)
            .head(20)
        )
        graph_data['value_mil'] = graph_data['value'] / 1_000_000

        chart = (
            alt.Chart(graph_data)
            .mark_bar(color='steelblue')
            .encode(
                x=alt.X('value_mil:Q', 
                        title='Trade Value (Mil USD)',
                        axis=alt.Axis(format='.1f')),  # 1 decimal, e.g., 1.2M
                y=alt.Y('partner_name:N', sort=None, title='Partner'),
                tooltip=[alt.Tooltip('partner_name:N'), alt.Tooltip('value:Q', format='.3s')]  # Full value on hover
            )
            .properties(height=500, title='Top Trade Flows (in Millions)')
        )

        st.altair_chart(chart, width='stretch')

        make_globe(trades, export_type='partner')

        # imports['value'] = imports['value'].map('${:,.2f}'.format)
        # imports['weight'] = imports['weight'].map('{:,.2f}'.format)
        # imports["trade_type"] = "import"
        # st.dataframe(imports, width='stretch')

with tab4:

    timeseries  = population 
    timeseries = timeseries[['name', 'value', 'year']].dropna()

    timeseries = timeseries.sort_values(['name', 'year'])  # This ensures proper order

    timeseries['pct_growth'] = timeseries.groupby('name')['value'].pct_change() * 100
    timeseries['pct_growth'] = timeseries['pct_growth'].round(2)

    timeseries['cum_growth'] = (
        timeseries.groupby('name')['value']
        .apply(lambda x: (x / x.iloc[0] - 1) * 100)
        .round(2)
    )

    col1, col2 = st.columns([1, 1])
    with col1:
        chart = (alt.Chart(timeseries)
            .mark_line(strokeWidth=3)
            .encode(
                x=alt.X('year:Q', title='Year'),
                y=alt.Y('value:Q', title='Population'),
                color=alt.Color('name:N', title='Country')  # Color by country
            )
            .properties(
                title='Population over time per country',
                height=600,
            )
            .interactive()
        )
        st.altair_chart(chart, use_container_width=True)

    with col2:
        chart = (alt.Chart(timeseries)
            .mark_bar(size=25)
            .encode(
                x=alt.X('year:O', title='Year', axis=alt.Axis(labelAngle=0)),
                y=alt.Y('pct_growth:Q', title='Population Growth %'),
                color=alt.Color('name:N', title='Country'),
                tooltip=['name', 'year', 'pct_growth']
            )
            .properties(
                title='Population Growth % over Time per Country',
                height=600,
                width=800
            )
            .interactive()
        )
        st.altair_chart(chart, use_container_width=True)


    cum_chart = (alt.Chart(timeseries)
        .mark_bar(size=12)
        .encode(
            x=alt.X('year:O', title='Year', scale=alt.Scale(padding=0.4)),
            y=alt.Y('cum_growth:Q', title='Cumulative Growth %'),
            color=alt.Color('name:N', title='Country'),
            tooltip=['name', 'year', 'cum_growth']
        )
        .properties(
            title='Cumulative Population Growth % over Time per Country',
            height=400,
            width=800
        )
        .interactive()
    )
    st.altair_chart(cum_chart, use_container_width=True)


    max_year_data = timeseries.loc[timeseries.groupby('name')['year'].idxmax()]
    pie_chart = (alt.Chart(max_year_data)
        .mark_arc(outerRadius=100)
        .encode(
            theta=alt.Theta('value:Q', title='Population'),
            color=alt.Color('name:N', title='Country'),
            tooltip=['name', 'value']
        )
        .properties(
            title=f'Population Share by Country ({max_year_data["year"].max()} - Latest Year)'
        )
    )
    st.altair_chart(pie_chart, use_container_width=True)


    st.dataframe(timeseries)

with tabx:
    tables = {
        'Trades': trades,
        'Product': products,
        'Countries': countries,
        'Population': population,
    }
    for table in tables:
        st.text(f'{table} | records ({len(tables[table])})')
        st.dataframe(tables[table], width='stretch')
        col1, col2, col3 = st.columns(3)
        st.divider()








# with col2:


# col1, col2 = st.columns([1, 1])

# with col1:










# example_data = {
#     'reporter_iso3': ['World'] * 12,
#     'partner_name': ['USA', 'China', 'India', 'Germany', 'Japan', 'UK', 'France', 'Italy', 'South Korea', 'UAE', 'Saudi Arabia', 'Iran'],
#     'partner_iso3': ['USA', 'CHN', 'IND', 'DEU', 'JPN', 'GBR', 'FRA', 'ITA', 'KOR', 'ARE', 'SAU', 'IRN'],
#     'continent': ['North America', 'Asia', 'Asia', 'Europe', 'Asia', 'Europe', 'Europe', 'Europe', 'Asia', 'Asia', 'Asia', 'Asia'],
#     'value': np.random.uniform(50, 600, 12),  # $M trade volume
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
# fig.update_layout(height=600)
# st.plotly_chart(fig, width='stretch')

