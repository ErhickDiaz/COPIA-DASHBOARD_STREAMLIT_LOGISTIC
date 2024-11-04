import streamlit as st
from shareplum import Site
from shareplum import Office365
import pandas as pd
from io import StringIO
from shareplum.site import Version
from datetime import datetime
from streamlit_echarts import st_echarts
import numpy as np
import plotly.express as px
from streamlit_autorefresh import st_autorefresh
import base64

def main():
    
    # Cargar y codificar la imagen
    def load_image(image_file):
        with open(image_file, "rb") as f:
            data = f.read()
            return base64.b64encode(data).decode()
        
    # Función para cargar el archivo CSS
    def load_css(file_name):
        with open(file_name) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

    # Cargar el CSS
    load_css('style.css')

    # Cargar y mostrar la imagen en la barra lateral
    st.sidebar.image("OsitoTierno.png", use_column_width=True)  # Asegúrate de que la imagen esté en la misma carpeta

     # Ruta del logo
    logo = "IDEAL.jfif"  # Asegúrate de que la ruta sea correcta
    # Obtener la imagen codificada
    logo_base64 = load_image(logo)

    st.markdown(f"""
            <div style="display: flex; align-items: center;">
                <img src="data:image/jpeg;base64,{logo_base64}" alt="Logo" style="width: 240px; margin-right: 10px;">
                <h1 style="margin-bottom: 0;">Logística: Monitoreo transportación pre - primaria.</h1>
            </div>
        """, unsafe_allow_html=True)
    
    def actividad_sharepoint():
        
        username = "kevin.urtubia01@grupobimbo.com"
        password = "Soporte.2028"
        sharepoint_url = "https://gbconnect.sharepoint.com"
        site_url = "/sites/Torredetransportacin"

        # Autenticación en SharePoint
        authcookie = Office365(sharepoint_url, username=username, password=password).GetCookies()
        site = Site(sharepoint_url + site_url, version=Version.v365, authcookie=authcookie)
        folder_url2 = "Documentos Compartidos/Dashboard_Streamlit/Tractos_Transito_Pre_primaria"
        folder_url = "Documentos Compartidos/Dashboard_Streamlit/Saturacin_WMS"

        # Acceder a la carpeta de SharePoint
        folder = site.Folder(folder_url)
        folder2 = site.Folder(folder_url2)

        saturacion_csv = folder.get_file(f"historico_saturaciones_{datetime.now().strftime('%Y_%m_%d')}.csv").decode("utf-8")
        T_Pre_Primaria_csv = folder2.get_file("Tractos_Transito_Pre_Primaria.csv").decode("utf-8")
        # Convertir el contenido del archivo a DataFrame de pandas
      
        df_satu = pd.read_csv(StringIO(saturacion_csv))

        Saturación = df_satu.iloc[-1]['Saturación']

        df_T_Pre_Primaria = pd.read_csv(StringIO(T_Pre_Primaria_csv))
    
        return df_satu, Saturación, df_T_Pre_Primaria 

    df_satu, saturacion, df_T_Pre_Primaria = actividad_sharepoint()
    n_pallets = df_satu["N° de pallets"].iloc[-1]

    # Configurar las opciones del gráfico de ECharts
    def get_gauge_options(saturacion, n_pallets):
        return {
            "series": [
                {
                    "type": "gauge",
                    "startAngle": 90,
                    "endAngle": -270,
                    "pointer": {"show": False},
                    "progress": {
                        "show": True,
                        "overlap": False,
                        "roundCap": True,
                        "clip": False,
                        "itemStyle": {
                            #"borderWidth": 1,
                            "borderColor": "#464646"
                        }
                    },
                    "axisLine": {
                        "lineStyle": {"width": 10}
                    },
                    "splitLine": {
                        "show": False,
                        "distance": 0,
                        "length": 10
                    },
                    "axisTick": {"show": False},
                    "axisLabel": {"show": False},
                    "data": [
                        {
                            "value": saturacion,
                            "name": "Planta IDEAL \n \n % LPNs Empacados",
                            "title": {"offsetCenter": ["0%", "-50%"],
                            "fontWeight": "bold"},  # Texto en negrita para el título},
                            "detail": {
                                "valueAnimation": True,
                                "offsetCenter": ["0%", "-10%"],
                                
                            }
                        },
                        {"value": int(n_pallets), "name": "N° de pallets", "title": {"offsetCenter": ["0%", "20%"],"fontWeight": "bold"}, "detail": {"offsetCenter": ["0%", "45%"]},  "formatter": "{value}", "show": True}
                        #{"value": 0, "name": "Planta NB", "title": {"offsetCenter": ["0%", "10%"]}, "detail": {"offsetCenter": ["0%", "30%"]}},
                        #{"value": 0, "name": "Barcel", "title": {"offsetCenter": ["0%", "50%"]}, "detail": {"offsetCenter": ["0%", "70%"]}}
                    ],
                    "title": {"fontSize": 14},
                    "detail": {
                        "width": 70,
                        "height": 20,
                        "fontSize": 20,
                        "color": "inherit",
                        "borderColor": "inherit",
                        "borderRadius": 40,
                        "borderWidth": 1,
                        "formatter": "{value}"
                    }
                }
            ]
        }
    
    # Dividir la página en tres columnas con un ancho personalizado
    col1, col2, col3= st.columns([1, 2, 2])

        # Renderizar el gráfico ECharts en la primera columna
    with col1:
        st_echarts(get_gauge_options(saturacion, n_pallets), height=400)

        #df_pallets = pd.DataFrame({
         #   'Nodo': ['HKL - Planta Ideal', "HKN - NutraBien ","GAX - Planta Chillán", "Barcel"], 
          #  "Fecha": [df_satu["Fecha"].iloc[-1],df_satu["Fecha"].iloc[-1],df_satu["Fecha"].iloc[-1],df_satu["Fecha"].iloc[-1]],
           # 'Pallets Empacados': [df_satu["N° de pallets"].iloc[-1], np.nan, np.nan, np.nan]  # número de filas del archivo descargado
            #})

        # Centrando la tabla usando un ancho ajustado con la columna
        #st.write("<div style='text-align: center;'>", unsafe_allow_html=True)  # Centrado manual
        #st.dataframe(df_pallets)  # Mostrar el DataFrame centrado en la columna
        #st.write("</div>", unsafe_allow_html=True)  # Cierre del div

    # Segunda columna: Gráfico de la saturación diaria
    with col2:
        if not df_satu.empty:

            #st.markdown("<h3 style='text-align: center;'>% de Pallets Empacados en planta Ideal</h3>", unsafe_allow_html=True)
            #st.write("<div style='text-align: center;'>", unsafe_allow_html=True)  # Centrado manual

            # Crear gráfico de línea
            fig_daily = px.line(df_satu, x='Fecha', y='Saturación', title=f'Saturación Operativa: % de Pallets Empacados en planta Ideal - {pd.Timestamp.now().date()}')
        
            fig_daily.update_traces(
                mode='lines+markers',   # Modo líneas con puntos
                marker=dict(symbol='circle', size=8, color="#1C306A"),  # Puntos como círculos
                line=dict(dash='solid', color='#1C306A')  # Línea sólida y color específico
            )

            # Actualizar el layout para ajustar tamaños y negrita
            fig_daily.update_layout(
                title=dict(
                    text=f'% de Pallets Empacados en planta Ideal - {pd.Timestamp.now().date()}',
                    font=dict(size=20, color='black', family="Arial", weight='bold'),  # Tamaño y negrita del título
                    x=0.5,  # Centrar el título
                    xanchor='center'
                ),
                yaxis_title=dict(
                    text="(%)", 
                    font=dict(size=20, color='black', family="Arial", weight='bold')  # Tamaño y negrita del label eje Y
                ),
                xaxis_title=dict(
                    text="", 
                    font=dict(size=14, color='black', family="Arial", weight='bold')  # Tamaño y negrita del label eje X
                ),
                yaxis=dict(
                    tickmode='linear',
                    tick0=0,
                    dtick=10,
                    tickfont=dict(size=14, color='black', family="Arial", weight='bold'),  # Negrita en los valores del eje Y
                    titlefont=dict(color='black')
                ),
                xaxis=dict(
                    tickfont=dict(size=14, color='black', family="Arial", weight='bold'),  # Negrita en los valores del eje X
                    titlefont=dict(color='black')
                ),
                hoverlabel=dict(
                    font_size=18,  # Tamaño de la fuente de las etiquetas
                    font_family="Arial",  # Tipo de letra de las etiquetas
                    font_color="white",  # Color de letra en las etiquetas
                    bgcolor="black"  # Fondo de las etiquetas
                ),

                annotations=[
                    # Primera línea de la anotación
                    dict(
                        text="Nota: No se está considerando los pallets de Planta Ideal empacados que se encuentran en la cinta automática,",
                        xref="paper", yref="paper",
                        x=0.5, y=-0.25,  # Posición de la primera línea
                        showarrow=False,
                        font=dict(size=12, color='grey'),
                        xanchor='center'
                    ),
                    # Segunda línea de la anotación
                    dict(
                        text="porque no es posible obtener esa información desde WMS y está relacionado a proceso operativos.",
                        xref="paper", yref="paper",
                        x=0.5, y=-0.30,  # Posición de la segunda línea
                        showarrow=False,
                        font=dict(size=12, color='grey'),
                        xanchor='center'
                    )
                ]
            )

                     
            fig_daily.add_hline(y=100, line_dash="dash", line_color="red", line_width=2)
            fig_daily.add_hline(y=0, line_dash="dash", line_color="#FFFFFF", line_width=2)
            fig_daily.add_hline(y=80, line_dash="dash", line_color="#FFA500", line_width=2)

            # Mostrar gráfico en Streamlit
            st.plotly_chart(fig_daily)

# Tercera columna: Mensaje u otra información adicional
    with col3:
        
         # Título centrado
        st.markdown("<h3 style='text-align: center;'>Tractos en tránsito planta - CEDIS</h3>", unsafe_allow_html=True)
        st.write("<div style='text-align: center;'>", unsafe_allow_html=True)  # Centrado manual

        st.markdown(
        """
        <style>
        .blue-header table {
            width: 100%;
            border-collapse: collapse;
        }
        .blue-header thead tr th {
            background-color: #1C306A;
            color: white;
            padding: 10px;
        }
        .blue-header tbody tr td {
            text-align: center;
            padding: 10px;
            font-weight: bold;  /* Negrita */
        }
        </style>
        """, unsafe_allow_html=True
        )

        # Convertir el DataFrame a HTML con estilo personalizado
        st.markdown(df_T_Pre_Primaria.style.set_table_attributes('class="blue-header"').to_html(), unsafe_allow_html=True)

        #st.dataframe(df_T_Pre_Primaria)  # Mostrar el DataFrame centrado en la columna
        #st.write("</div>", unsafe_allow_html=True)  # Cierre del div

    
    