import streamlit as st
import pandas as pd
import os

def main():

    st.set_page_config(
        page_title="Dashboard Logística Inversa",
        layout="wide"
    )

    st.title("📦 Dashboard Logística Inversa")
    st.markdown("Control de Transferencias CTL")

    st.divider()

    # -----------------------------
    # CARGA DE DATOS
    # -----------------------------
    @st.cache_data
    def cargar_datos():
        ruta = os.path.join("data", "CL-tess.txt")
        df = pd.read_csv(ruta, sep=",")
        return df

    df = cargar_datos()

    st.success("✅ Datos cargados correctamente")

    # -----------------------------
    # DEBUG
    # -----------------------------
    st.subheader("Vista previa de datos")
    st.dataframe(df.head(20))

    # Mostrar columnas (MUY IMPORTANTE AHORA)
    st.subheader("Columnas detectadas")
    st.write(df.columns)
