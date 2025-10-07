import dash
from dash import dcc, html
import plotly.express as px
import geopandas as gpd
import pandas as pd
import unidecode
import numpy as np
import matplotlib.pyplot as plt
import io
import base64
import matplotlib.patheffects as path_effects


# --- RUTAS ---
csv_path = "resumen_departamentos.csv"
shp_path = r"shapefiles/MGN_DPTO_POLITICO.shp"  # o usa .geojson si lo conviertes

# --- CARGA DE DATOS ---
df = pd.read_csv(csv_path, encoding="utf-8")
gdf = gpd.read_file(shp_path)

# --- LIMPIEZA Y ESTANDARIZACIÓN ---
df['DEPARTAMENTO_DE_OFERTA_DEL_PROGRAMA'] = (
    df['DEPARTAMENTO_DE_OFERTA_DEL_PROGRAMA']
    .astype(str)
    .str.upper()
    .str.strip()
    .map(unidecode.unidecode)
)

gdf['DPTO_CNMBR'] = (
    gdf['DPTO_CNMBR']
    .astype(str)
    .str.upper()
    .str.strip()
    .map(unidecode.unidecode)
)

# --- UNIÓN DE DATOS ---
merged_programas = gdf.merge(
    df,
    left_on='DPTO_CNMBR',
    right_on='DEPARTAMENTO_DE_OFERTA_DEL_PROGRAMA',
    how='left'
)

# 🔹 FUNCIONES DE MAPAS (Plotly)
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
            x=0.9,
            xanchor='left',
            len=0.7,
            thickness=15,
            tickfont=dict(color='white'),
            bgcolor='rgba(0,0,0,0)'
        )
    )
    return fig

# 1️⃣ Mapa coroplético
fig1 = px.choropleth(
    merged_programas,
    geojson=merged_programas.geometry,
    locations=merged_programas.index,
    color='CANTIDAD_PROGRAMAS',
    hover_name='DPTO_CNMBR',
    projection='mercator',
    color_continuous_scale='thermal',
    title='Cantidad de Programas por Departamento'
)
fig1 = dark_layout(fig1)

# 2️⃣ Escala logarítmica
merged_programas['LOG_CANTIDAD'] = merged_programas['CANTIDAD_PROGRAMAS'].apply(
    lambda x: np.log(x) if pd.notnull(x) and x > 0 else None
)
fig2 = px.choropleth(
    merged_programas,
    geojson=merged_programas.geometry,
    locations=merged_programas.index,
    color='LOG_CANTIDAD',
    hover_name='DPTO_CNMBR',
    projection='mercator',
    color_continuous_scale='thermal',
    title='Cantidad de Programas (Escala Logarítmica)'
)
fig2 = dark_layout(fig2)

# ======================
# 🔹 MARCADORES PROPORCIONALES (Matplotlib)
# ======================

def generar_mapa_marcadores():
    fig, ax = plt.subplots(figsize=(12, 10))
    merged_programas.plot(color='black', edgecolor='white', linewidth=0.5, ax=ax)

    max_size = 2000
    for _, row in merged_programas.iterrows():
        x, y = row['geometry'].centroid.coords[0]
        cantidad = row['CANTIDAD_PROGRAMAS'] if pd.notnull(row['CANTIDAD_PROGRAMAS']) else 0
        size = (cantidad / merged_programas['CANTIDAD_PROGRAMAS'].max()) * max_size
        ax.scatter(x, y, s=size, color='red', alpha=0.6, edgecolor='white')

    for _, row in merged_programas.iterrows():
        x, y = row['geometry'].centroid.coords[0]
        text = ax.text(
            x, y, row['DPTO_CNMBR'], fontsize=9, color='white',
            ha='center', weight='bold'
        )
        text.set_path_effects([path_effects.withStroke(linewidth=1.5, foreground='black')])

    ax.set_title('Cantidad de Programas por Departamento (Marcadores Proporcionales)', fontsize=16, color='white')
    ax.set_axis_off()
    fig.patch.set_facecolor('black')
    ax.set_facecolor('black')

    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', facecolor='black')
    plt.close(fig)
    buf.seek(0)
    encoded = base64.b64encode(buf.read()).decode("utf-8")
    return f"data:image/png;base64,{encoded}"

mapa_marcadores_img = generar_mapa_marcadores()

# 3️⃣ Promedio de matriculados
fig3 = px.choropleth(
    merged_programas,
    geojson=merged_programas.geometry,
    locations=merged_programas.index,
    color='PROMEDIO_MATRICULADOS',
    hover_name='DPTO_CNMBR',
    projection='mercator',
    color_continuous_scale='thermal',
    title='Promedio de Matriculados por Departamento'
)
fig3 = dark_layout(fig3)

# 4️⃣ Top 25%
threshold = merged_programas['CANTIDAD_PROGRAMAS'].quantile(0.75)
merged_programas['TOP25'] = merged_programas['CANTIDAD_PROGRAMAS'] > threshold

fig4 = px.choropleth(
    merged_programas,
    geojson=merged_programas.geometry,
    locations=merged_programas.index,
    color='TOP25',
    hover_name='DPTO_CNMBR',
    projection='mercator',
    color_continuous_scale=['#4B0082', '#FF4500'],
    title='Departamentos en el Top 25% de Programas'
)
fig4 = dark_layout(fig4)

# ======================
# 🔹 DASH APP
# ======================

app = dash.Dash(__name__)
server = app.server  

app.title = "Visualización de Matriculas en educacion superior, para estudiantes colombianos desde 2015 a 2023."

# Función para crear las secciones con cajas
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
                    'color': '#EEE', 'fontSize': '20px', 'lineHeight': '1.6',
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
        html.H1("Taller 2 - Visualización de Matriculas en educacion superior, para estudiantes colombianos desde 2015 a 2023.",
                style={'textAlign': 'center', 'color': '#FFA500', 'marginBottom': '10px'}),
        html.H3("Hecho por Juan Aguirre",
                style={'textAlign': 'center', 'color': '#DDD', 'marginBottom': '30px'})
    ], style={'backgroundColor': '#111', 'padding': '20px', 'boxShadow': '0 2px 5px rgba(255,255,255,0.1)'}),

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
            dcc.Tab(label='Marcadores Proporcionales', value='tab3', children=[
                html.Div([
                    html.Div([
                        html.Div([
                            html.Img(src=mapa_marcadores_img,
                                     style={'width': '95%', 'borderRadius': '15px', 'boxShadow': '0 0 15px #333'})
                        ], style={
                            'flex': '3',
                            'backgroundColor': '#2f2f2f',
                            'borderRadius': '15px',
                            'padding': '20px',
                            'marginRight': '20px',
                            'boxShadow': '0 0 15px rgba(255,255,255,0.1)',
                            'textAlign': 'center'
                        }),
                        html.Div([
                            html.P("Este mapa utiliza círculos proporcionales al número de programas por departamento. "
                                   "Los tamaños reflejan la concentración académica, destacando Antioquia, Bogotá y Valle del Cauca "
                                   "como los principales centros educativos.",
                                   style={'color': '#EEE', 'fontSize': '20px', 'lineHeight': '1.6',
                                          'textAlign': 'justify', 'padding': '20px'})
                        ], style={
                            'flex': '1',
                            'backgroundColor': '#3a3a3a',
                            'borderRadius': '15px',
                            'boxShadow': '0 0 15px rgba(255,255,255,0.1)',
                            'display': 'flex',
                            'alignItems': 'center'
                        })
                    ], style={'display': 'flex', 'flexDirection': 'row', 'padding': '30px'})
                ], style={'backgroundColor': '#1a1a1a'})
            ]),
            dcc.Tab(label='Promedio de Matriculados', value='tab4',
                    children=layout_tab(fig3, "Similar a las visualizaciones anteriores, vemos que los estados con menor cantidad de diversidad, y en este caso de promedio de matriculados, se encuentran los departamentos de Vichada, Guainia y Amazonas como estados con menor promedio, y los promedios mas altos se concentran en los departamentos de Antioquia, Cesar, Atlantico y Valle del Cauca.")),
            dcc.Tab(label='Top 25% de Programas', value='tab5',
                    children=layout_tab(fig4, "Departamentos que se encuentran dentro del 25% superior en cantidad de programas académicos ofrecidos."))
        ]
    )
], style={'backgroundColor': '#000', 'color': 'white'})

if __name__ == "__main__":
    app.run(debug=True)
