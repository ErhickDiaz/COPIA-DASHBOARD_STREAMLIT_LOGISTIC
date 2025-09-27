import streamlit as st
import pandas as pd
from io import StringIO
from datetime import datetime
from streamlit_echarts import st_echarts
import plotly.express as px
import base64
from github import Github

# ==============================
# CONFIGURACIÓN GITHUB
# ==============================
GITHUB_TOKEN = "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"
REPO_NAME = "ErhickDiaz/COPIA-DASHBOARD_STREAMLIT_LOGISTIC"
GITHUB_FOLDER = "data"
GITHUB_BRANCH = "main"

# ==============================
# FUNCIONES
# ==============================
def load_image(image_file):
    """Carga una imagen local y la codifica en base64"""
    with open(image_file, "rb") as f:
        data = f.read()
        return base64.b64encode(data).decode()

def load_css(file_name):
    """Carga un archivo CSS local"""
    with open(file_name) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

def actividad_github():
    """Carga los CSVs de GitHub directamente"""
    repo = Github(GITHUB_TOKEN).get_repo(REPO_NAME)
    fecha_local = datetime.now().strftime('%Y_%m_%d')

    saturacion_file = f"{GITHUB_FOLDER}/historico_saturaciones_{fecha_local}.csv"
    tractos_file = f"{GITHUB_FOLDER}/Tractos_Transito_Pre_Primaria.csv"

    # Leer saturación
    try:
        contenido_satu = repo.get_contents(saturacion_file, ref=GITHUB_BRANCH).decoded_content.decode()
        df_satu = pd.read_csv(StringIO(contenido_satu))
        saturacion = df_satu["Saturación"].iloc[-1]
        n_pallets = df_satu["N° de pallets"].iloc[-1]
    except:
        df_satu = pd.DataFrame(columns=["Fecha","Saturación","N° de pallets"])
        saturacion = 0
        n_pallets = 0

    # Leer tractos en tránsito
    try:
        contenido_tractos = repo.get_contents(tractos_file, ref=GITHUB_BRANCH).decoded_content.decode()
        df_T_Pre_Primaria = pd.read_csv(StringIO(contenido_tractos))
    except:
        df_T_Pre_Primaria = pd.DataFrame(columns=['Desde','Hasta','Estado','LPNs Env','Bult. Env','Hora de salida'])

    return df_satu, saturacion, n_pallets, df_T_Pre_Primaria

def get_gauge_options(saturacion, n_pallets):
    """Configura opciones del gauge ECharts"""
    return {
        "series": [
            {
                "type": "gauge",
                "startAngle": 90,
                "endAngle": -270,
                "pointer": {"show": False},
                "progress": {"show": True, "roundCap": True},
                "axisLine": {"lineStyle": {"width": 10}},
                "splitLine": {"show": False},
                "axisTick": {"show": False},
                "axisLabel": {"show": False},
                "data": [
                    {
                        "value": saturacion,
                        "name": "Planta IDEAL \n % LPNs Empacados",
                        "title": {"offsetCenter": ["0%", "-50%"], "fontWeight": "bold"},
                        "detail": {"valueAnimation": True, "offsetCenter": ["0%", "-10%"]}
                    },
                    {
                        "value": int(n_pallets),
                        "name": "N° de pallets",
                        "title": {"offsetCenter": ["0%", "20%"], "fontWeight": "bold"},
                        "detail": {"offsetCenter": ["0%", "45%"]},
                        "formatter": "{value}",
                        "show": True
                    }
                ],
                "title": {"fontSize": 14},
                "detail": {"width": 70, "height": 20, "fontSize": 20, "color": "inherit", "borderColor": "inherit",
                           "borderRadius": 40, "borderWidth": 1, "formatter": "{value}"}
            }
        ]
    }

# ==============================
# MAIN
# ==============================
def main():
    st.set_page_config(layout="wide")
    load_css('style.css')  # carga CSS local
    
    # Sidebar y logo
    try:
        st.sidebar.image("OsitoTierno.png", use_column_width=True)
    except:
        st.sidebar.text("Imagen OsitoTierno.png no encontrada")

    try:
        logo_base64 = load_image("IDEAL.jfif")
        st.markdown(f"""
            <div style="display: flex; align-items: center;">
                <img src="data:image/jpeg;base64,{logo_base64}" alt="Logo" style="width: 240px; margin-right: 10px;">
                <h1 style="margin-bottom: 0;">Logística: Monitoreo transportación pre - primaria.</h1>
            </div>
        """, unsafe_allow_html=True)
    except:
        st.markdown("<h1>Logística: Monitoreo transportación pre - primaria.</h1>", unsafe_allow_html=True)

    # Cargar datos desde GitHub
    df_satu, saturacion, n_pallets, df_T_Pre_Primaria = actividad_github()

    # Dividir columnas
    col1, col2, col3 = st.columns([1, 2, 2])

    # -------- Columna 1: Gauge ECharts --------
    with col1:
        st_echarts(get_gauge_options(saturacion, n_pallets), height=400)

    # -------- Columna 2: Gráfico de saturación diaria --------
    with col2:
        if not df_satu.empty:
            fig_daily = px.line(df_satu, x='Fecha', y='Saturación', 
                                title=f'Saturación Operativa - {datetime.now().date()}')
            fig_daily.update_traces(mode='lines+markers', marker=dict(symbol='circle', size=8, color="#1C306A"),
                                    line=dict(dash='solid', color='#1C306A'))
            fig_daily.update_layout(title_x=0.5)
            fig_daily.add_hline(y=100, line_dash="dash", line_color="red")
            fig_daily.add_hline(y=80, line_dash="dash", line_color="#FFA500")
            st.plotly_chart(fig_daily)

    # -------- Columna 3: Tabla tractos --------
    with col3:
        st.markdown("<h3 style='text-align: center;'>Tractos en tránsito planta - CEDIS</h3>", unsafe_allow_html=True)
        st.markdown(df_T_Pre_Primaria.style.set_table_attributes('class="blue-header"').to_html(), unsafe_allow_html=True)

if __name__ == "__main__":
    main()
