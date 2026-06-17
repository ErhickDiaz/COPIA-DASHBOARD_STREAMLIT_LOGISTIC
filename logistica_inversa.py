import streamlit as st
import pandas as pd
import os


def main():
    st.title("♻️ Logística Inversa")
    st.success("✅ Módulo cargado correctamente")



st.set_page_config(
    page_title="Dashboard Logística Inversa",
    layout="wide"
)

st.title("📦 Dashboard Logística Inversa")
st.markdown("Control de Transferencias CTL")

st.divider()

@st.cache_data
def cargar_datos():
    ruta = os.path.join("data", "CL_16062026_1.xlsx")
    df = pd.read_excel(ruta)
    return df

df = cargar_datos()

st.success("✅ Datos cargados correctamente")

st.subheader("Vista previa de datos")
st.dataframe(df.head(20))
``
