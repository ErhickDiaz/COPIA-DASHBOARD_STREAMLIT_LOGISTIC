import streamlit as st
import requests
from io import StringIO
import pandas as pd
import plotly.express as px
from datetime import datetime
import pytz



# ==============================
# CONFIG
# ==============================
RAW_MAXCUBE_URL = (
    "https://raw.githubusercontent.com/"
    "ErhickDiaz/COPIA-DASHBOARD_STREAMLIT_LOGISTIC/"
    "main/data/MAXCUBE_Primaria.csv"
)

ZONA_HORARIA = "America/Santiago"

# ==============================
# CARGA DE DATOS
# ==============================


@st.cache_data(ttl=60)  # 60 segundos = 1 minuto

def cargar_maxcube():
    resp = requests.get(RAW_MAXCUBE_URL, timeout=60)
    resp.raise_for_status()

    df = pd.read_csv(StringIO(resp.text))

    # Normalizaciones clave
    df["Fecha de despacho"] = pd.to_datetime(
        df["Fecha de despacho"], dayfirst=True, errors="coerce"
    )

    df["Hora_num"] = pd.to_datetime(
        df["Hora de despacho"], format="%H:%M:%S", errors="coerce"
    ).dt.hour

    df["Bultos despachados"] = pd.to_numeric(
        df["Bultos despachados"], errors="coerce"
    ).fillna(0)

    df["Viajes"] = pd.to_numeric(
        df["Viajes"], errors="coerce"
    ).fillna(0)

    return df


# ==============================
# APP
# ==============================
def main():

    st.session_state["ultima_actualizacion_real"] = datetime.now(
        pytz.timezone(ZONA_HORARIA)
    )

    st.title("📦 MaxCube – Transporte Primaria")
    st.caption("Fuente: Oracle WMS → GitHub (MAXCUBE_Primaria.csv)")

    df = cargar_maxcube()

    if df.empty:
        st.warning("El archivo MAXCUBE no contiene registros.")
        return

    # ==============================
    # SIDEBAR – FILTROS
    # ==============================
    with st.sidebar:
        st.header("🔎 Filtros")

        # Fechas
        f_min = df["Fecha de despacho"].min()
        f_max = df["Fecha de despacho"].max()

        f_ini, f_fin = st.date_input(
            "Fecha de despacho",
            value=(f_min.date(), f_max.date()),
        )

        # Horas
        h_ini, h_fin = st.slider(
            "Hora de despacho",
            min_value=0,
            max_value=23,
            value=(0, 23)
        )

        # Proveedor
        proveedores = sorted(df["PROVEEDOR"].dropna().unique())
        prov_sel = st.multiselect("Proveedor", proveedores)

        # Destino
        destinos = sorted(df["Destino Agencia concat"].dropna().unique())
        dest_sel = st.multiselect("Destino", destinos)

    # ==============================
    # APLICAR FILTROS
    # ==============================
    f = df.copy()

    f = f[
        (f["Fecha de despacho"].dt.date >= f_ini) &
        (f["Fecha de despacho"].dt.date <= f_fin)
    ]

    f = f[f["Hora_num"].between(h_ini, h_fin)]

    if prov_sel:
        f = f[f["PROVEEDOR"].isin(prov_sel)]

    if dest_sel:
        f = f[f["Destino Agencia concat"].isin(dest_sel)]

    # ==============================
    # KPIs
    # ==============================
    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "📦 Bultos despachados",
        f"{int(f['Bultos despachados'].sum()):,}".replace(",", ".")
    )

    c2.metric(
        "🚚 Viajes",
        f"{int(f['Viajes'].sum()):,}".replace(",", ".")
    )

    c3.metric(
        "🏢 Proveedores",
        f["PROVEEDOR"].nunique()
    )

    c4.metric(
        "📍 Destinos",
        f["Destino Agencia concat"].nunique()
    )

    st.divider()


    ###### GRAFICO POR DESTINO/AGENCIA####

    st.subheader("📈 Bultos despachados por despacho (día y hora)")

    # Construir datetime completo (día + hora)
    f["Despacho_dt"] = pd.to_datetime(
        f["Fecha de despacho"].astype(str) + " " + f["Hora de despacho"].astype(str),
        errors="coerce"
    )
    
    # Ordenar por tiempo para que la línea conecte correctamente
    f_plot = (
        f.dropna(subset=["Despacho_dt", "Bultos despachados"])
         .sort_values("Despacho_dt")
    )
    
    fig = px.scatter(
        f_plot,
        x="Despacho_dt",
        y="Bultos despachados",
        color="Destino Agencia concat",
        hover_data=["Destino Agencia concat", "PROVEEDOR", "Bitácora", "Nro carga"],
        labels={
            "Despacho_dt": "Día y hora",
            "Bultos despachados": "Bultos"
        }
    )
    
    # ✅ Unir puntos con línea
    fig.update_traces(mode="lines+markers")
    
    # ✅ Eje Y fijo + marcas claras
    fig.update_yaxes(
        range=[0, 5000],                 # fija el rango
        tickmode="array",
        tickvals=[0, 500, 1000, 5000],   # marcas solicitadas
        ticktext=["0", "500", "1000", "5000"],
        zeroline=True,
        zerolinewidth=2
    )
    
    fig.update_layout(
        height=520,
        xaxis_title="Día y hora",
        yaxis_title="Bultos",
    )
    
    st.plotly_chart(fig, use_container_width=True)

    # ==============================
    # GRÁFICO POR HORA
    # ==============================
    #st.subheader("⏱️ Bultos despachados por hora")

    #gh = (
    #    f.groupby("Hora_num", as_index=False)["Bultos despachados"]
    #    .sum()
    #)

    #fig = px.bar(
    #    gh,
     #   x="Hora_num",
    #    y="Bultos despachados",
     #   labels={
     #       "Hora_num": "Hora del día",
      #      "Bultos despachados": "Bultos"
     #   }
    #)

    #st.plotly_chart(fig, use_container_width=True)

    # ==============================
    # TABLA DETALLE
    # ==============================
    st.subheader("📄 Detalle de despachos")
    st.dataframe(f, use_container_width=True, height=520)

    # ==============================
    # DESCARGA
    # ==============================
    st.download_button(
        "⬇️ Descargar CSV filtrado",
        data=f.to_csv(index=False).encode("utf-8"),
        file_name="maxcube_filtrado.csv",
        mime="text/csv"
    )


if __name__ == "__main__":
    main()


