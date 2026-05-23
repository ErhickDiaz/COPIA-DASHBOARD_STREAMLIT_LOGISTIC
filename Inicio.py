import streamlit as st
import base64
import pandas as pd

def main():

    # ───── FUNCIONES ─────
    def load_image(image_file):
        with open(image_file, "rb") as f:
            data = f.read()
            return base64.b64encode(data).decode()

    def load_css(file_name):
        with open(file_name) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

    load_css('style.css')

    # ───── LOGO + HEADER ─────
    logo = "IDEAL.jfif"
    logo_base64 = load_image(logo)

    st.sidebar.image("OsitoTierno.png", use_column_width=True)

    st.markdown(f"""
        <div style="display: flex; align-items: center;">
            <img src="data:image/jpeg;base64,{logo_base64}" style="width: 220px; margin-right: 15px;">
            <h1>Logística: Torre de Monitoreo</h1>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("### 📊 Nacional | Tablero Estratégico de Gestión Distribución Primaria | Resumen")

    # ───── CARGA DE DATOS ─────
    # 👉 aquí debes apuntar a tu CSV de GitHub o local
    try:
        df = pd.read_csv("data/MAXCUBE_Primaria.csv")
    except:
        st.warning("⚠️ No hay datos disponibles")
        return

    # ───── KPIs ─────
    bultos = int(df["Bultos despachados"].sum())
    viajes = len(df)
    capacidad = viajes * 1800 if viajes > 0 else 0
    maxcube = round((bultos / capacidad) * 100, 1) if capacidad > 0 else 0
    gap = round(100 - maxcube, 1)

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("🚛 Viajes", viajes)
    col2.metric("📦 Bultos", f"{bultos:,}")
    col3.metric("📊 MaxCube", f"{maxcube}%")
    col4.metric("⚠️ Gap 100%", f"{gap}%")

    # ───── SEMÁFORO ─────
    if maxcube < 80:
        st.error("🔴 Uso bajo de capacidad")
    elif maxcube < 90:
        st.warning("🟠 Uso medio")
    else:
        st.success("🟢 Uso óptimo")

    # ───── TABLA CENTRAL ─────
    st.markdown("### 📍 Distribución por destino")

    ranking = (
        df.groupby("Destino Agencia concat")["Bultos despachados"]
        .sum()
        .sort_values(ascending=False)
        .reset_index()
    )

    st.dataframe(ranking, use_container_width=True)

    # ───── BLOQUE INFERIOR ─────
    col1, col2 = st.columns(2)

    with col1:
        st.metric("📦 Promedio por viaje", round(bultos / viajes, 1) if viajes > 0 else 0)
        st.metric("🚛 Total despachos", viajes)

    with col2:
        st.metric("📊 Uso MaxCube", f"{maxcube}%")
        st.metric("📉 Gap operacional", f"{gap}%")

    # ───── ALERTAS ─────
    st.markdown("### ⚠️ Control operativo")

    errores = df[df["Bultos despachados"] == 0]

    if not errores.empty:
        st.dataframe(errores[["Nro carga", "Destino Agencia concat"]])
    else:
        st.success("✅ Sin cargas con bultos en 0")


if __name__ == "__main__":
    main()
