import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="Dashboard Logística Inversa",
    layout="wide"
)

# -----------------------------
# TÍTULO / PORTADA
# -----------------------------
st.title("📦 Dashboard Logística Inversa")
st.markdown("Control de Transferencias CTL")

st.divider()

# -----------------------------
# CARGA DE DATOS
# -----------------------------
@st.cache_data
def cargar_datos():
    df = pd.read_excel("data/CL_16062026_1.xlsx")
    return df

df = cargar_datos()

st.success("✅ Datos cargados correctamente")

# -----------------------------
# VISTA PREVIA (DEBUG)
# -----------------------------
st.subheader("Vista previa de datos")
st.dataframe(df.head(20))
