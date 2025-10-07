import dash
from dash import dcc, html
import plotly.express as px
import geopandas as gpd
import pandas as pd
import unidecode
import numpy as np
import json
import os

# --- RUTAS ---
csv_path = "resumen_departamentos.csv"
shp_path = r"shapefiles/MGN_DPTO_POLITICO.shp"
merged_path = "merged_programas.geojson"

# --- CARGA Y PROCESAMIENTO ---
if os.path.exists(merged_path):
    print("🔹 Cargando merge simplificado desde archivo...")
    gdf = gpd.read_file(merged_path)
else:
    print("🔹 Procesando shapefile y CSV...")
    df = pd.read_csv(csv_path, encoding="utf-8")
    gdf = gpd.read_file(shp_path)

    # Simplificar geometrías (reduce tamaño sin perder forma)
    gdf["geometry"] = gdf.simplify(0.02, preserve_topology=True)

    # Limpieza
    df["DEPARTAMENTO_DE_OFERTA_DEL_PROGRAMA"] = (
        df["DEPARTAMENTO_DE_OFERTA_DEL_PROGRAMA"]
        .astype(str)
        .str.upper()
        .str.strip()
        .map(unidecode.unidecode)
    )

    gdf["DPTO_CNMBR"] = (
        gdf["DPTO_CNMBR"]
        .astype(str)
        .str.upper()
        .str.strip()
        .map(unidecode.unidecode)
    )

    merged_programas = gdf.merge(
        df,
        left_on="DPTO_CNMBR",
        right_on="DEPARTAMENTO_DE_OFERTA_DEL_PROGRAMA",
        how="left"
    )

    merged_programas.to_file(merged_path, driver="GeoJSON")
    gdf = merged_programas

print("✅ Datos cargados correctamente.")

# ======================
# 🔹 FUNCIONES
# ======================

def dark_layout(fig):
    fig.update_geos(fitbounds="locations", visible=False, bgcolor='rgba(0,0,0,1)')
    fig.update_layout(
        margin={"r": 0, "t": 40, "l": 0, "b": 0},
        paper_bgcolor='black',
        plot_bgcolor='black',
        font_color='white',
        geo=dict(bgcolor='rgba(0,0,0,1)'),
        coloraxis_colorbar=dict(
            title="",
            len=0.7,
            thickness=15,
            tickfont=dict(color='white')
        )
    )
    return fig


# ======================
# 🔹 MAPAS (Plotly)
# ======================

# 1️⃣ Mapa coroplético
fig1 = px.choropleth(
    gdf,
    geojson=json.loads(gdf.to_json()),
    locations=gdf.index,
    color="CANTIDAD_PROGRAMAS",
    hover_name="DPTO_CNMBR",
    projection="mercator",
    color_continuous_scale="thermal",
    title="Cantidad de Programas por Departamento"
)
fig1 = dark_layout(fig1)

# 2️⃣ Escala logarítmica
gdf["LOG_CANTIDAD"] = gdf["CANTIDAD_PROGRAMAS"].apply(
    lambda x: np.log(x) if pd.notnull(x) and x > 0 else None
)
fig2 = px.choropleth(
    gdf,
    geojson=json.loads(gdf.to_json()),
    locations=gdf.index,
    color="LOG_CANTIDAD",
    hover_name="DPTO_CNMBR",
    projection="mercator",
    color_continuous_scale="thermal",
    title="Cantidad de Programas (Escala Logarítmica)"
)
fig2 = dark_layout(fig2)

# 3️⃣ Promedio de matriculados
fig3 = px.choropleth(
    gdf,
    geojson=json.loads(gdf.to_json()),
    locations=gdf.index,
    color="PROMEDIO_MATRICULADOS",
    hover_name="DPTO_CNMBR",
    projection="mercator",
    color_continuous_scale="thermal",
    title="Promedio de Matriculados por Departamento"
)
fig3 = dark_layout(fig3)

# 4️⃣ Top 25%
threshold = gdf["CANTIDAD_PROGRAMAS"].quantile(0.75)
gdf["TOP25"] = gdf["CANTIDAD_PROGRAMAS"] > threshold

fig4 = px.choropleth(
    gdf,
    geojson=json.loads(gdf.to_json()),
    locations=gdf.index,
    color="TOP25",
    hover_name="DPTO_CNMBR",
    projection="mercator",
    color_continuous_scale=["#4B0082", "#FF4500"],
    title="Departamentos en el Top 25% de Programas"
)
fig4 = dark_layout(fig4)

# ======================
# 🔹 DASH APP
# ======================

app = dash.Dash(__name__)
server = app.server

def layout_tab(fig, text):
    return html.Div([
        html.Div([
            html.Div(
                [dcc.Graph(figure=fig, style={'height': '85vh'})],
                style={
                    'flex': '3',
                    'backgroundColor': '#2f2f2f',
                    'borderRadius': '15px',
                    'padding': '20px',
                    'marginRight': '20px',
                    'boxShadow': '0 0 15px rgba(255,255,255,0.1)'
                }
            ),
            html.Div(
                [html.P(text, style={
                    'color': '#EEE', 'fontSize': '18px', 'lineHeight': '1.6',
                    'textAlign': 'justify', 'padding': '20px'
                })],
                style={
                    'flex': '1',
                    'backgroundColor': '#3a3a3a',
                    'borderRadius': '15px',
                    'boxShadow': '0 0 15px rgba(255,255,255,0.1)',
                    'display': 'flex',
                    'alignItems': 'center'
                }
            )
        ], style={'display': 'flex', 'flexDirection': 'row', 'padding': '30px'})
    ], style={'backgroundColor': '#1a1a1a'})

app.layout = html.Div([
    html.Div([
        html.H1("Taller 2 - Visualización de Matrículas en Educación Superior (2015–2023)",
                style={'textAlign': 'center', 'color': '#FFA500', 'marginBottom': '10px'}),
        html.H3("Hecho por Juan Aguirre",
                style={'textAlign': 'center', 'color': '#DDD', 'marginBottom': '30px'})
    ], style={'backgroundColor': '#111', 'padding': '20px'}),

    dcc.Tabs(
        id="tabs",
        value='tab1',
        colors={"border": "#333", "primary": "#FFA500", "background": "#000"},
        style={'fontSize': '18px', 'color': 'white'},
        children=[
            dcc.Tab(label='Mapa Coroplético', value='tab1',
                    children=layout_tab(fig1, "Si observamos de manera lineal, vemos que los departamentos de Antioquia y Valle del Cauca parecen ser los que tienen mayor prevalencia en la cantidad de programas por departamento, mientras que el resto del pais tiene una cantidad menor a 12.000 programas. Por temas de visualizacion, se usara en escala logaritmica para que se observen las diferencias en departamentos.")),
            dcc.Tab(label='Mapa Logarítmico', value='tab2',
                    children=layout_tab(fig2, "Usando la escala logaritmica, vemos como se diferencia con respecto al anterior, donde a pesar que Antioquia y Valle del Cauca con los mayores promedios, departamentos como Santander y Atlantico son los siguientes con mayor cantidad de programas por departamento. Por otro lado, los estados azules, con prevalencia en el interior y los Llanos Orientales, vemos una menor cantidad de diversidad, con Vichada y Vaupes siendo aquellos con menor cantidad.")),
            dcc.Tab(label='Promedio de Matriculados', value='tab3',
                    children=layout_tab(fig3, "Similar a las visualizaciones anteriores, vemos que los estados con menor cantidad de diversidad, y en este caso de promedio de matriculados, se encuentran los departamentos de Vichada, Guainia y Amazonas como estados con menor promedio, y los promedios mas altos se concentran en los departamentos de Antioquia, Cesar, Atlantico y Valle del Cauca.")),
            dcc.Tab(label='Top 25% de Programas', value='tab4',
                    children=layout_tab(fig4, "Departamentos que se encuentran dentro del 25% superior en cantidad de programas académicos ofrecidos."))
        ]
    )
], style={'backgroundColor': '#000', 'color': 'white'})

if __name__ == "__main__":
    app.run(debug=True)
