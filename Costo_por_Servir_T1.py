import io
import re
import unicodedata
from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

# =========================================================
# CONFIGURACION
# =========================================================
CSV_URL = (
    "https://raw.githubusercontent.com/ErhickDiaz/"
    "COPIA-DASHBOARD_STREAMLIT_LOGISTIC/main/data/"
    "Costo_por_Servir_T1.csv"
)

st.set_page_config(
    page_title="Costo por Servir T1",
    page_icon="🚚",
    layout="wide",
)

# =========================================================
# ESTILOS
# =========================================================
st.markdown(
    """
    <style>
    .stApp { background: #07111f; color: #f8fafc; }
    [data-testid="stMetric"] {
        background: #0d1d30;
        border: 1px solid #31506b;
        border-radius: 14px;
        padding: 14px 16px;
    }
    [data-testid="stMetricLabel"] { color: #a9bfd2; }
    [data-testid="stMetricValue"] { color: #ffffff; }
    .t1-subtitle { color:#b7c8d8; margin-top:-8px; }
    .t1-badge {
        display:inline-block; background:#10243a; color:#86efac;
        border:1px solid #3d607d; border-radius:10px;
        padding:8px 12px; font-weight:700;
    }
    div[data-testid="stDataFrame"] {
        border: 1px solid #31506b;
        border-radius: 12px;
        overflow: hidden;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# =========================================================
# UTILIDADES
# =========================================================
def normalizar_nombre(texto):
    texto = str(texto).strip().lower()
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", " ", texto).strip()


def encontrar_columna(df, opciones, obligatoria=True):
    mapa = {normalizar_nombre(c): c for c in df.columns}
    for opcion in opciones:
        objetivo = normalizar_nombre(opcion)
        if objetivo in mapa:
            return mapa[objetivo]
    for norm, original in mapa.items():
        if any(normalizar_nombre(op) in norm for op in opciones):
            return original
    if obligatoria:
        raise KeyError(f"No se encontro ninguna columna equivalente a: {opciones}")
    return None


def a_numero(serie):
    if pd.api.types.is_numeric_dtype(serie):
        return pd.to_numeric(serie, errors="coerce").fillna(0.0)
    limpio = (
        serie.astype(str)
        .str.replace('="', "", regex=False)
        .str.replace('"', "", regex=False)
        .str.replace("$", "", regex=False)
        .str.replace(" ", "", regex=False)
        .str.replace(r"\.(?=\d{3}(?:\D|$))", "", regex=True)
        .str.replace(",", ".", regex=False)
    )
    return pd.to_numeric(limpio, errors="coerce").fillna(0.0)


def formato_clp(valor):
    return f"$ {valor:,.0f}".replace(",", ".")


@st.cache_data(ttl=300, show_spinner=False)
def cargar_datos(url):
    # Se agrega un parametro para evitar cache externo obsoleto.
    separadores = [",", ";"]
    ultimo_error = None
    for sep in separadores:
        try:
            df = pd.read_csv(
                f"{url}?v={datetime.now().strftime('%Y%m%d%H%M')}",
                sep=sep,
                encoding="utf-8-sig",
                engine="python",
            )
            if len(df.columns) > 3:
                return df
        except Exception as exc:
            ultimo_error = exc
    raise RuntimeError(f"No fue posible leer el CSV: {ultimo_error}")


def preparar_datos(df):
    col_fecha = encontrar_columna(df, ["Fecha", "Fecha de despacho"])
    col_hora = encontrar_columna(df, ["Hora", "Hora de despacho"], False)
    col_destino = encontrar_columna(df, ["Destino", "Destino Agencia concat"])
    col_proveedor = encontrar_columna(df, ["Proveedor", "PROVEEDOR"])
    col_flete = encontrar_columna(df, ["Valor Flete", "Flete COSTO AC", "Costo Flete"])
    col_bdesp = encontrar_columna(df, ["Bultos despachados"])
    col_vdesp = encontrar_columna(df, ["Costo de los bultos despachados", "Valor despachado"])
    col_bemp = encontrar_columna(df, ["Bultos empacados"])
    col_vemp = encontrar_columna(df, ["Costo de los bultos empacados", "Valor empacado"])
    col_bitacora = encontrar_columna(df, ["Bitacora", "Bitácora"])
    col_carga = encontrar_columna(df, ["Nro carga", "Nro de Carga", "Numero carga"])

    out = pd.DataFrame({
        "Fecha": pd.to_datetime(df[col_fecha], dayfirst=True, errors="coerce"),
        "Hora": df[col_hora].astype(str).replace("nan", "") if col_hora else "",
        "Destino": df[col_destino].fillna("SIN DESTINO").astype(str).str.strip(),
        "Proveedor": df[col_proveedor].fillna("SIN PROVEEDOR").astype(str).str.strip(),
        "Valor Flete": a_numero(df[col_flete]),
        "Bultos despachados": a_numero(df[col_bdesp]),
        "Valor despachado": a_numero(df[col_vdesp]),
        "Bultos empacados": a_numero(df[col_bemp]),
        "Valor empacado": a_numero(df[col_vemp]),
        "Bitacora": df[col_bitacora].fillna("").astype(str).str.replace(r"\.0$", "", regex=True),
        "Nro carga": df[col_carga].fillna("").astype(str).str.strip(),
    })

    out["CxQ"] = 0.0
    mascara = out["Valor empacado"] > 0
    out.loc[mascara, "CxQ"] = (
        out.loc[mascara, "Valor Flete"] /
        out.loc[mascara, "Valor empacado"]
    )
    out["Estado cruce"] = out["Valor Flete"].gt(0).map(
        {True: "Flete cruzado", False: "Sin COSTO AC"}
    )
    out["Diferencia bultos"] = (
        out["Bultos despachados"] - out["Bultos empacados"]
    )
    return out.sort_values(["Fecha", "Hora"], ascending=[False, False])


# =========================================================
# CARGA
# =========================================================
try:
    base = preparar_datos(cargar_datos(CSV_URL))
except Exception as exc:
    st.error(f"No fue posible cargar Costo_por_Servir_T1.csv: {exc}")
    st.stop()

# =========================================================
# CABECERA Y FILTROS
# =========================================================
st.markdown("### T1 · TRANSPORTE PRIMARIO")
st.title("Costo por Servir T1")
st.markdown(
    '<div class="t1-subtitle">Cruce por Nro carga: MAXCUBE + OB_ORDER_DTL + VIAJES WMS, COSTO columna AC</div>',
    unsafe_allow_html=True,
)
st.caption(f"Fuente actualizada desde GitHub · {len(base):,} viajes en la base".replace(",", "."))

f1, f2, f3, f4 = st.columns([1.2, 1.5, 2.2, 1.0])
with f1:
    fechas_validas = base["Fecha"].dropna()
    if fechas_validas.empty:
        rango = None
    else:
        rango = st.date_input(
            "Fecha despacho",
            value=(fechas_validas.min().date(), fechas_validas.max().date()),
        )
with f2:
    destinos = st.multiselect("Destino", sorted(base["Destino"].dropna().unique()))
with f3:
    proveedores = st.multiselect("Proveedor", sorted(base["Proveedor"].dropna().unique()))
with f4:
    estado = st.selectbox("Cruce flete", ["Todos", "Flete cruzado", "Sin COSTO AC"])

busqueda = st.text_input("Buscar Nro carga o Bitacora", placeholder="Ej.: HKOOB37669712 o 120962")

filtrado = base.copy()
if rango and isinstance(rango, (tuple, list)) and len(rango) == 2:
    inicio, fin = pd.Timestamp(rango[0]), pd.Timestamp(rango[1])
    filtrado = filtrado[filtrado["Fecha"].between(inicio, fin + pd.Timedelta(days=1) - pd.Timedelta(seconds=1))]
if destinos:
    filtrado = filtrado[filtrado["Destino"].isin(destinos)]
if proveedores:
    filtrado = filtrado[filtrado["Proveedor"].isin(proveedores)]
if estado != "Todos":
    filtrado = filtrado[filtrado["Estado cruce"] == estado]
if busqueda.strip():
    q = busqueda.strip().lower()
    filtrado = filtrado[
        filtrado["Nro carga"].str.lower().str.contains(q, na=False, regex=False) |
        filtrado["Bitacora"].str.lower().str.contains(q, na=False, regex=False)
    ]

# =========================================================
# KPI
# =========================================================
viajes = len(filtrado)
flete_total = filtrado["Valor Flete"].sum()
valor_total = filtrado["Valor empacado"].sum()
cxq_global = flete_total / valor_total if valor_total > 0 else 0
cobertura = filtrado["Valor Flete"].gt(0).mean() if viajes else 0

k1, k2, k3, k4, k5, k6 = st.columns(6)
k1.metric("Viajes", f"{viajes:,}".replace(",", "."))
k2.metric("Valor empacado", formato_clp(valor_total))
k3.metric("Flete AC", formato_clp(flete_total))
k4.metric("CxQ global", f"{cxq_global:.2%}" if valor_total > 0 else "Pendiente")
k5.metric("Cobertura flete", f"{cobertura:.1%}")
k6.metric("Bultos empacados", f"{filtrado['Bultos empacados'].sum():,.0f}".replace(",", "."))

# =========================================================
# GRAFICOS
# =========================================================
izq, der = st.columns(2)
with izq:
    por_destino = (
        filtrado.groupby("Destino", as_index=False)
        .agg(Flete=("Valor Flete", "sum"), Valor=("Valor empacado", "sum"), Viajes=("Nro carga", "count"))
    )
    por_destino["CxQ"] = por_destino["Flete"].div(por_destino["Valor"]).where(por_destino["Valor"] > 0, 0)
    por_destino = por_destino.sort_values("CxQ", ascending=False).head(15)
    fig = px.bar(por_destino, x="Destino", y="CxQ", color="CxQ", title="CxQ por destino", color_continuous_scale="Tealgrn")
    fig.update_yaxes(tickformat=".1%")
    fig.update_layout(paper_bgcolor="#0d1d30", plot_bgcolor="#0d1d30", font_color="#f8fafc", coloraxis_showscale=False)
    st.plotly_chart(fig, use_container_width=True)

with der:
    por_proveedor = (
        filtrado.groupby("Proveedor", as_index=False)
        .agg(Flete=("Valor Flete", "sum"), Valor=("Valor empacado", "sum"), Viajes=("Nro carga", "count"))
    )
    por_proveedor["CxQ"] = por_proveedor["Flete"].div(por_proveedor["Valor"]).where(por_proveedor["Valor"] > 0, 0)
    por_proveedor = por_proveedor.sort_values("Flete", ascending=False).head(12)
    fig2 = px.bar(por_proveedor, x="Proveedor", y="Flete", color="CxQ", title="Flete y CxQ por proveedor", color_continuous_scale="Sunset")
    fig2.update_layout(paper_bgcolor="#0d1d30", plot_bgcolor="#0d1d30", font_color="#f8fafc")
    st.plotly_chart(fig2, use_container_width=True)

# =========================================================
# DETALLE
# =========================================================
st.subheader("Detalle de viajes MAXCUBE")
detalle = filtrado.copy()
detalle["Fecha"] = detalle["Fecha"].dt.strftime("%d/%m/%Y").fillna("")
detalle["CxQ"] = detalle["CxQ"].map(lambda x: f"{x:.2%}" if x > 0 else "Pendiente")
for c in ["Valor Flete", "Valor despachado", "Valor empacado"]:
    detalle[c] = detalle[c].map(formato_clp)
for c in ["Bultos despachados", "Bultos empacados", "Diferencia bultos"]:
    detalle[c] = detalle[c].map(lambda x: f"{x:,.0f}".replace(",", "."))

columnas = [
    "Fecha", "Hora", "Destino", "Proveedor", "Valor Flete",
    "Bultos despachados", "Valor despachado", "Bultos empacados",
    "Valor empacado", "CxQ", "Bitacora", "Nro carga", "Estado cruce",
]
st.dataframe(
    detalle[columnas],
    use_container_width=True,
    hide_index=True,
    height=520,
    column_config={
        "Estado cruce": st.column_config.TextColumn("Cruce COSTO AC"),
        "Nro carga": st.column_config.TextColumn("Nro carga", width="large"),
        "Proveedor": st.column_config.TextColumn("Proveedor", width="large"),
    },
)

# Descarga del filtro visible
csv = filtrado.to_csv(index=False, sep=";", encoding="utf-8-sig").encode("utf-8-sig")
st.download_button(
    "Descargar detalle filtrado",
    data=csv,
    file_name="Costo_por_Servir_T1_filtrado.csv",
    mime="text/csv",
)
