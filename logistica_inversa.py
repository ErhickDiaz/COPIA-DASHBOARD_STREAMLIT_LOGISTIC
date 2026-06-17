import streamlit as st
import pandas as pd
import os

def main():

    st.title("📦 Dashboard Logística Inversa")
    st.markdown("Control de Transferencias CTL")

    st.divider()

    # -----------------------------
    # CARGA DE DATOS
    # -----------------------------
    @st.cache_data
    def cargar_datos():
        ruta = os.path.join("data", "CL_16062026_1.csv")

        df = pd.read_csv(
            ruta,
            sep=",",
            encoding="latin-1",
            engine="python",
            on_bad_lines="skip"
        )

        return df

    df = cargar_datos()

    st.success("✅ Datos cargados correctamente")

    # -----------------------------
    # LIMPIEZA BÁSICA
    # -----------------------------
    df.columns = df.columns.str.strip()

    # convertir columnas numéricas
    df["CANT_ENVIADA"] = pd.to_numeric(df["CANT_ENVIADA"], errors="coerce")
    df["CANT_RECIBIDA"] = pd.to_numeric(df["CANT_RECIBIDA"], errors="coerce")
    df["DIFERENCIA"] = pd.to_numeric(df["DIFERENCIA"], errors="coerce")

    # -----------------------------
    # KPIs
    # -----------------------------
    total_transferencias = df["NUM_TRANSF"].nunique()
    total_registros = len(df)

    receptados = df[df["ESTADO"] == "Receptado"].shape[0]
    cancelados = df[df["ESTADO"] == "Cancelado"].shape[0]

    diferencias = df[df["DIFERENCIA"] != 0].shape[0]

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Transferencias únicas", total_transferencias)
    col2.metric("Registros totales", total_registros)
    col3.metric("Receptados", receptados)
    col4.metric("Con diferencia ⚠️", diferencias)

    st.divider()

    # -----------------------------
    # ALERTA DE DIFERENCIAS
    # -----------------------------
    st.subheader("⚠️ Transferencias con diferencia")

    df_diff = df[df["DIFERENCIA"] != 0]

    if df_diff.empty:
        st.success("✅ Sin diferencias detectadas")
    else:
        st.warning(f"Se encontraron {len(df_diff)} registros con diferencia")
        st.dataframe(df_diff.head(50))

    st.divider()

    # -----------------------------
    # FILTROS
    # -----------------------------
    st.subheader("🔍 Filtros")

    estados = st.multiselect(
        "Filtrar por estado",
        options=df["ESTADO"].unique(),
        default=df["ESTADO"].unique()
    )

    df_filtrado = df[df["ESTADO"].isin(estados)]

    # -----------------------------
    # TABLA
    # -----------------------------
    st.subheader("📊 Datos filtrados")
    st.dataframe(df_filtrado.head(100))

    # -----------------------------
    # AGRUPACIÓN POR DESTINO
    # -----------------------------
    st.subheader("📦 Envíos por destino")

    df_destino = (
        df_filtrado.groupby("DESTINO")["CANT_ENVIADA"]
        .sum()
        .sort_values(ascending=False)
        .head(10)
    )

    st.bar_chart(df_destino)

    # -----------------------------
    # DEBUG
    # -----------------------------
    with st.expander("🛠 Debug"):
        st.write("Columnas detectadas:")
        st.write(df.columns)
