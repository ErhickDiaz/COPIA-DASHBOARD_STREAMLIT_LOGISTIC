import streamlit as st
import pandas as pd
import os
from io import StringIO
from datetime import datetime
from PIL import Image, UnidentifiedImageError
from streamlit_echarts import st_echarts
import numpy as np
import plotly.express as px
import pytz
import base64
import requests


# =========================================================
# CONFIG GITHUB RAW
# =========================================================
GITHUB_USER = "ErhickDiaz"
GITHUB_REPO = "COPIA-DASHBOARD_STREAMLIT_LOGISTIC"
GITHUB_BRANCH = "main"
GITHUB_FOLDER = "data"

BASE_RAW_URL = (
    f"https://raw.githubusercontent.com/"
    f"{GITHUB_USER}/{GITHUB_REPO}/{GITHUB_BRANCH}/{GITHUB_FOLDER}"
)


# =========================================================
# FUNCIONES PARA LECTURA DESDE GITHUB RAW
# =========================================================
@st.cache_data(ttl=180)
def leer_csv_github_raw(filename):
    """
    Lee un CSV público desde GitHub RAW.
    Evita usar PyGithub en Streamlit Cloud.
    """
    try:
        url = f"{BASE_RAW_URL}/{filename}"

        response = requests.get(
            url,
            timeout=30,
            headers={
                "Cache-Control": "no-cache",
                "Pragma": "no-cache"
            }
        )

        response.raise_for_status()

        csv_string = response.content.decode("utf-8-sig", errors="replace")
        df = pd.read_csv(StringIO(csv_string))

        return df

    except Exception as e:
        st.warning(f"No se pudo cargar {filename} desde GitHub RAW.")
        st.caption(f"Archivo buscado: {filename}")
        st.caption(f"URL RAW: {BASE_RAW_URL}/{filename}")
        st.exception(e)
        return pd.DataFrame()


# =========================================================
# FUNCIONES AUXILIARES VISUALES
# =========================================================
def load_image_base64(image_file):
    """
    Carga una imagen local y la convierte a base64.
    Si no existe, devuelve None para evitar que la app falle.
    """
    try:
        base_dir = os.path.dirname(__file__)
        img_path = os.path.join(base_dir, image_file)

        if not os.path.exists(img_path):
            return None

        with open(img_path, "rb") as f:
            data = f.read()
            return base64.b64encode(data).decode()

    except Exception:
        return None


def load_css(file_name):
    """
    Carga CSS local si existe.
    Si no existe, la app continúa sin romper.
    """
    try:
        base_dir = os.path.dirname(__file__)
        css_path = os.path.join(base_dir, file_name)

        if os.path.exists(css_path):
            with open(css_path, encoding="utf-8") as f:
                st.markdown(
                    f"<style>{f.read()}</style>",
                    unsafe_allow_html=True
                )
        else:
            st.sidebar.warning(f"No se encontró el archivo CSS: {file_name}")

    except Exception as e:
        st.sidebar.warning(f"No se pudo cargar CSS: {e}")


def load_sidebar_image(image_filename):
    """
    Carga una imagen en sidebar si existe.
    """
    try:
        base_dir = os.path.dirname(__file__)
        img_path = os.path.join(base_dir, image_filename)

        if os.path.exists(img_path):
            try:
                img = Image.open(img_path)
                st.sidebar.image(img, use_container_width=True)
            except UnidentifiedImageError:
                st.sidebar.warning(
                    f"Archivo encontrado pero no es una imagen válida: {image_filename}"
                )
            except Exception as e:
                st.sidebar.error(f"Error inesperado al abrir la imagen: {e}")
        else:
            st.sidebar.warning(f"No se encontró la imagen: {image_filename}")

    except Exception as e:
        st.sidebar.warning(f"No se pudo cargar imagen lateral: {e}")


# =========================================================
# CARGA DE DATOS OPERATIVOS
# =========================================================
def actividad_github():
    """
    Carga los archivos de saturación y tractos desde GitHub RAW.
    """
    chile_tz = pytz.timezone("America/Santiago")
    fecha_local = datetime.now(chile_tz).strftime("%Y_%m_%d")

    saturacion_file = f"historico_saturaciones_{fecha_local}.csv"
    tractos_file = "Tractos_Transito_Pre_primaria.csv"

    df_satu = leer_csv_github_raw(saturacion_file)
    df_T_Pre_Primaria = leer_csv_github_raw(tractos_file)

    if not df_satu.empty:
        df_satu.columns = [str(c).strip() for c in df_satu.columns]

        if "Fecha" in df_satu.columns:
            df_satu["Fecha"] = pd.to_datetime(
                df_satu["Fecha"],
                errors="coerce"
            )

            ultima = df_satu["Fecha"].max()

            if pd.notna(ultima):
                st.session_state["ultima_actualizacion_real"] = ultima

        if "Saturación" in df_satu.columns:
            saturacion = df_satu["Saturación"].iloc[-1]
        else:
            saturacion = 0

        if "N° de pallets" in df_satu.columns:
            n_pallets = df_satu["N° de pallets"].iloc[-1]
        else:
            n_pallets = 0

    else:
        saturacion = 0
        n_pallets = 0

    return df_satu, saturacion, n_pallets, df_T_Pre_Primaria


# =========================================================
# GAUGE ECHARTS
# =========================================================
def get_gauge_options(saturacion, n_pallets):
    """
    Construye el gráfico tipo gauge.
    Protegido contra valores vacíos, None o texto.
    """
    saturacion = pd.to_numeric(saturacion, errors="coerce")
    n_pallets = pd.to_numeric(n_pallets, errors="coerce")

    if pd.isna(saturacion):
        saturacion = 0

    if pd.isna(n_pallets):
        n_pallets = 0

    saturacion = round(float(saturacion), 2)
    n_pallets = int(n_pallets)

    return {
        "series": [
            {
                "type": "gauge",
                "startAngle": 90,
                "endAngle": -270,
                "pointer": {
                    "show": False
                },
                "progress": {
                    "show": True,
                    "overlap": False,
                    "roundCap": True,
                    "clip": False,
                    "itemStyle": {
                        "borderColor": "#464646"
                    }
                },
                "axisLine": {
                    "lineStyle": {
                        "width": 10
                    }
                },
                "splitLine": {
                    "show": False,
                    "distance": 0,
                    "length": 10
                },
                "axisTick": {
                    "show": False
                },
                "axisLabel": {
                    "show": False
                },
                "data": [
                    {
                        "value": saturacion,
                        "name": "Planta IDEAL \n \n % LPNs Empacados",
                        "title": {
                            "offsetCenter": ["0%", "-50%"],
                            "fontWeight": "bold"
                        },
                        "detail": {
                            "valueAnimation": True,
                            "offsetCenter": ["0%", "-10%"]
                        }
                    },
                    {
                        "value": n_pallets,
                        "name": "N° de pallets",
                        "title": {
                            "offsetCenter": ["0%", "20%"],
                            "fontWeight": "bold"
                        },
                        "detail": {
                            "offsetCenter": ["0%", "45%"]
                        },
                        "formatter": "{value}",
                        "show": True
                    }
                ],
                "title": {
                    "fontSize": 14
                },
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


# =========================================================
# MAIN APP
# =========================================================
def main():

    # -----------------------------------------------------
    # CSS
    # -----------------------------------------------------
    load_css("style.css")

    # -----------------------------------------------------
    # SIDEBAR IMAGE
    # -----------------------------------------------------
    load_sidebar_image("OsitoTierno.png")

    # -----------------------------------------------------
    # LOGO Y TÍTULO
    # -----------------------------------------------------
    logo_base64 = load_image_base64("IDEAL.jfif")

    if logo_base64:
        st.markdown(
            f"""
            <div style="display: flex; align-items: center;">
                <img src="data:image/jpeg;base64,{logo_base64}" 
                     alt="Logo" 
                     style="width: 240px; margin-right: 10px;">
                <h1 style="margin-bottom: 0;">
                    Logística: Monitoreo transportación pre - primaria.
                </h1>
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.title("Logística: Monitoreo transportación pre - primaria.")

    st.caption("Fuente: GitHub RAW /data")

    # -----------------------------------------------------
    # BOTÓN ACTUALIZAR
    # -----------------------------------------------------
    if st.sidebar.button("🔄 Actualizar datos"):
        st.cache_data.clear()
        st.rerun()

    # -----------------------------------------------------
    # CARGA DATOS
    # -----------------------------------------------------
    df_satu, saturacion, n_pallets, df_T_Pre_Primaria = actividad_github()

    # -----------------------------------------------------
    # COLUMNAS PRINCIPALES
    # -----------------------------------------------------
    col1, col2, col3 = st.columns([1, 2, 2])

    # =====================================================
    # COLUMNA 1: GAUGE
    # =====================================================
    with col1:
        st_echarts(
            get_gauge_options(saturacion, n_pallets),
            height=400
        )

    # =====================================================
    # COLUMNA 2: SATURACIÓN DIARIA
    # =====================================================
    with col2:
        if not df_satu.empty:
            if "Fecha" in df_satu.columns and "Saturación" in df_satu.columns:

                df_satu["Fecha"] = pd.to_datetime(
                    df_satu["Fecha"],
                    errors="coerce"
                )

                df_satu["Saturación"] = pd.to_numeric(
                    df_satu["Saturación"],
                    errors="coerce"
                )

                df_satu_plot = df_satu.dropna(
                    subset=["Fecha", "Saturación"]
                ).copy()

                if not df_satu_plot.empty:

                    chile_tz = pytz.timezone("America/Santiago")
                    fecha_titulo = datetime.now(chile_tz).strftime("%d/%m/%Y")

                    fig_daily = px.line(
                        df_satu_plot,
                        x="Fecha",
                        y="Saturación",
                        title=f"% de Pallets Empacados en planta Ideal - {fecha_titulo}"
                    )

                    fig_daily.update_traces(
                        mode="lines+markers",
                        marker=dict(
                            symbol="circle",
                            size=8,
                            color="#1C306A"
                        ),
                        line=dict(
                            dash="solid",
                            color="#1C306A"
                        )
                    )

                    fig_daily.update_layout(
                        title=dict(
                            text=f"% de Pallets Empacados en planta Ideal - {fecha_titulo}",
                            font=dict(
                                size=20,
                                color="black",
                                family="Arial"
                            ),
                            x=0.5,
                            xanchor="center"
                        ),
                        yaxis_title=dict(
                            text="(%)",
                            font=dict(
                                size=20,
                                color="black",
                                family="Arial"
                            )
                        ),
                        xaxis_title=dict(
                            text="",
                            font=dict(
                                size=14,
                                color="black",
                                family="Arial"
                            )
                        ),
                        yaxis=dict(
                            tickmode="linear",
                            tick0=0,
                            dtick=10,
                            tickfont=dict(
                                size=14,
                                color="black",
                                family="Arial"
                            ),
                            titlefont=dict(
                                color="black"
                            )
                        ),
                        xaxis=dict(
                            tickfont=dict(
                                size=14,
                                color="black",
                                family="Arial"
                            ),
                            titlefont=dict(
                                color="black"
                            )
                        ),
                        hoverlabel=dict(
                            font_size=18,
                            font_family="Arial",
                            font_color="white",
                            bgcolor="black"
                        ),
                        annotations=[
                            dict(
                                text=(
                                    "Nota: No se está considerando los pallets de Planta Ideal "
                                    "empacados que se encuentran en la cinta automática,"
                                ),
                                xref="paper",
                                yref="paper",
                                x=0.5,
                                y=-0.25,
                                showarrow=False,
                                font=dict(
                                    size=12,
                                    color="grey"
                                ),
                                xanchor="center"
                            ),
                            dict(
                                text=(
                                    "porque no es posible obtener esa información desde WMS "
                                    "y está relacionado a procesos operativos."
                                ),
                                xref="paper",
                                yref="paper",
                                x=0.5,
                                y=-0.30,
                                showarrow=False,
                                font=dict(
                                    size=12,
                                    color="grey"
                                ),
                                xanchor="center"
                            )
                        ]
                    )

                    fig_daily.add_hline(
                        y=100,
                        line_dash="dash",
                        line_color="red",
                        line_width=2
                    )

                    fig_daily.add_hline(
                        y=0,
                        line_dash="dash",
                        line_color="#FFFFFF",
                        line_width=2
                    )

                    fig_daily.add_hline(
                        y=80,
                        line_dash="dash",
                        line_color="#FFA500",
                        line_width=2
                    )

                    st.plotly_chart(
                        fig_daily,
                        use_container_width=True
                    )

                else:
                    st.warning(
                        "El archivo de saturación no tiene datos válidos para graficar."
                    )

            else:
                st.warning(
                    "El archivo de saturación no contiene las columnas esperadas: Fecha y Saturación."
                )

        else:
            st.warning(
                "No se encontró información de saturación para la fecha actual."
            )

    # =====================================================
    # COLUMNA 3: TRACTOS EN TRÁNSITO
    # =====================================================
    with col3:
        st.markdown(
            """
            <h3 style='text-align: center;'>
                Tractos en tránsito planta - CEDIS
            </h3>
            """,
            unsafe_allow_html=True
        )

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
                text-align: center;
            }
            .blue-header tbody tr td {
                text-align: center;
                padding: 10px;
                font-weight: bold;
            }
            </style>
            """,
            unsafe_allow_html=True
        )

        if not df_T_Pre_Primaria.empty:
            try:
                html_table = (
                    df_T_Pre_Primaria
                    .style
                    .set_table_attributes('class="blue-header"')
                    .to_html()
                )

                st.markdown(
                    html_table,
                    unsafe_allow_html=True
                )

            except Exception as e:
                st.warning("No se pudo renderizar la tabla con estilo.")
                st.exception(e)
                st.dataframe(
                    df_T_Pre_Primaria,
                    use_container_width=True
                )
        else:
            st.warning(
                "No se encontró información de tractos en tránsito."
            )

    # -----------------------------------------------------
    # DIAGNÓSTICO OPCIONAL EN SIDEBAR
    # -----------------------------------------------------
    with st.sidebar.expander("🛠 Diagnóstico de fuente"):
        chile_tz = pytz.timezone("America/Santiago")
        fecha_local = datetime.now(chile_tz).strftime("%Y_%m_%d")

        st.write("Repositorio:", f"{GITHUB_USER}/{GITHUB_REPO}")
        st.write("Branch:", GITHUB_BRANCH)
        st.write("Carpeta:", GITHUB_FOLDER)
        st.write(
            "Archivo saturación:",
            f"historico_saturaciones_{fecha_local}.csv"
        )
        st.write(
            "Archivo tractos:",
            "Tractos_Transito_Pre_primaria.csv"
        )

        if "ultima_actualizacion_real" in st.session_state:
            st.write(
                "Última actualización real:",
                st.session_state["ultima_actualizacion_real"]
            )


# =========================================================
# EJECUCIÓN
# =========================================================
if __name__ == "__main__":
    main()
