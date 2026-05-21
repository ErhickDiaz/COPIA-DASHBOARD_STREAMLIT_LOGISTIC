import streamlit as st
import pandas as pd
from github import Github
from io import StringIO
from datetime import datetime
import pytz
import plotly.express as px


# =========================================================
# CONFIG
# =========================================================
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
REPO_NAME = "ErhickDiaz/COPIA-DASHBOARD_STREAMLIT_LOGISTIC"
GITHUB_FOLDER = "data"
ARCHIVO_MAXCUBE = "MAXCUBE_Primaria.csv"
ZONA_HORARIA = "America/Santiago"

# =========================================================
# REGLAS DE CAPACIDAD
# =========================================================
CAPACIDAD_100_DESTINO = {
    "ANTOFAGASTA": 1800,
    "CHILLAN": 1700,
    "CONCEPCION": 1700,
    "COPIAPO": 1750,
    "EL PINAR": 1250,
    "IQUIQUE": 1800,
    "LA SERENA": 1700,
    "LA SERENA / RUTA SOLITARIA 1059 LV": 1750,
    "LO ESPEJO": 1560,
    "LOS ANDES": 1560,
    "LOS ANGELES": 1700,
    "MELIPILLA": 1700,
    "OSORNO": 1800,
    "PTO MONTT": 1800,
    "PTO MONTT / RUTA SOLITARIA ELPAC": 1800,
    "RANCAGUA": 1700,
    "SAN FERNANDO": 660,
    "TALCA": 1560,
    "TEMUCO": 1750,
    "VALDIVIA": 1800,
    "VINA DEL MAR": 1664,
}

PROVEEDOR_CAP_2200 = "76746317-0/TRAILER LOGISTICS SPA"


# =========================================================
# GITHUB
# =========================================================
def leer_csv_github(repo, filename):
    try:
        file_content = repo.get_contents(f"{GITHUB_FOLDER}/{filename}")
        csv_string = file_content.decoded_content.decode("utf-8")
        return pd.read_csv(StringIO(csv_string))
    except Exception as e:
        st.error(f"No se pudo cargar {filename} desde GitHub: {e}")
        return pd.DataFrame()


# =========================================================
# CARGA Y ENRIQUECIMIENTO
# =========================================================
def cargar_maxcube():
    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(REPO_NAME)

    df = leer_csv_github(repo, ARCHIVO_MAXCUBE)

    if df.empty:
        return df

    # -------------------------
    # Normalización básica
    # -------------------------
    df.columns = [c.strip() for c in df.columns]

    # Asegurar columnas mínimas
    
    columnas_esperadas = [
    "Bitácora",
    "Nro carga",
    "Fecha de despacho",
    "Hora de despacho",
    "Destino Agencia concat",
    "PROVEEDOR",
    "Patente vehículo",   # ✅ NUEVO
    "Viajes",
    "Bultos despachados",
    ]

    for col in columnas_esperadas:
        if col not in df.columns:
            df[col] = ""

    # Si no existe patente en el CSV actual, la dejamos vacía
    if "Patente rampla" not in df.columns:
        df["Patente rampla"] = ""

    if "Patente vehículo" not in df.columns:
    df["Patente vehículo"] = ""

    # Fecha + hora real
    df["Fecha de despacho"] = pd.to_datetime(
        df["Fecha de despacho"],
        dayfirst=True,
        errors="coerce"
    )

    df["Hora de despacho"] = df["Hora de despacho"].astype(str)

    df["Fecha despacho dt"] = pd.to_datetime(
        df["Fecha de despacho"].dt.strftime("%d/%m/%Y") + " " + df["Hora de despacho"],
        dayfirst=True,
        errors="coerce"
    )
    # ✅ Formato visual de fecha (legible)
    df["Fecha de despacho"] = df["Fecha de despacho"].dt.strftime("%d/%m/%Y")

    # Numéricos
    df["Bultos despachados"] = pd.to_numeric(
        df["Bultos despachados"],
        errors="coerce"
    ).fillna(0)

    df["Viajes"] = pd.to_numeric(
        df["Viajes"],
        errors="coerce"
    ).fillna(1)

    # -------------------------
    # Campos temporales
    # -------------------------
    df["Fecha"] = df["Fecha despacho dt"].dt.date
    df["Semana"] = df["Fecha despacho dt"].dt.isocalendar().week.astype("Int64")
    df["Año-Semana"] = (
        df["Fecha despacho dt"].dt.isocalendar().year.astype(str)
        + "-W"
        + df["Fecha despacho dt"].dt.isocalendar().week.astype(str).str.zfill(2)
    )
    df["Mes"] = df["Fecha despacho dt"].dt.strftime("%Y-%m")

    # -------------------------
    # Capacidad / Uso / Gap
    # -------------------------
    df["Capacidad 100%"] = df["Destino Agencia concat"].map(CAPACIDAD_100_DESTINO)

    df.loc[
        df["PROVEEDOR"].astype(str).str.strip().str.upper() == PROVEEDOR_CAP_2200.upper(),
        "Capacidad 100%"
    ] = 2200

    df["Uso MaxCube %"] = (
        df["Bultos despachados"] / df["Capacidad 100%"] * 100
    ).round(2)

    df["Gap a 100%"] = df["Capacidad 100%"] - df["Bultos despachados"]

    # Orden ascendente base
    df = df.sort_values(
        ["Fecha despacho dt", "Destino Agencia concat", "Bitácora", "Nro carga"],
        ascending=[True, True, True, True]
    )

    return df


# =========================================================
# AUXILIARES
# =========================================================
def semaforo(valor):
    if pd.isna(valor):
        return "⚪"
    elif valor < 90:
        return "🔴"
    elif valor < 100:
        return "🟠"
    else:
        return "🟢"


def resumen_por_destino(f):
    if f.empty:
        return pd.DataFrame()

    resumen = (
        f.groupby("Destino Agencia concat", as_index=False)
        .agg(
            Bultos=("Bultos despachados", "sum"),
            Viajes=("Viajes", "sum"),
            Capacidad=("Capacidad 100%", "sum"),
            Gap=("Gap a 100%", "sum")
        )
    )

    resumen["Uso MaxCube %"] = (
        resumen["Bultos"] / resumen["Capacidad"] * 100
    ).round(2)

    resumen["Semáforo"] = resumen["Uso MaxCube %"].apply(semaforo)

    resumen = resumen.sort_values("Uso MaxCube %", ascending=True)
    return resumen


def resumen_por_patente(f):
    if f.empty or "Patente rampla" not in f.columns:
        return pd.DataFrame()

    f_pat = f.copy()
    f_pat = f_pat[f_pat["Patente rampla"].astype(str).str.strip() != ""]

    if f_pat.empty:
        return pd.DataFrame()

    resumen = (
        f_pat.groupby("Patente rampla", as_index=False)
        .agg(
            Destinos=("Destino Agencia concat", lambda x: " / ".join(sorted(set([str(v) for v in x if pd.notna(v) and str(v).strip() != ""])))),
            Proveedores=("PROVEEDOR", lambda x: " / ".join(sorted(set([str(v) for v in x if pd.notna(v) and str(v).strip() != ""])))),
            Bultos=("Bultos despachados", "sum"),
            Viajes=("Viajes", "sum"),
            Capacidad=("Capacidad 100%", "sum"),
            Gap=("Gap a 100%", "sum")
        )
    )

    resumen["Uso MaxCube %"] = (
        resumen["Bultos"] / resumen["Capacidad"] * 100
    ).round(2)

    resumen["Semáforo"] = resumen["Uso MaxCube %"].apply(semaforo)
    resumen = resumen.sort_values("Uso MaxCube %", ascending=True)

    return resumen


def metricas_globales(f):
    if f.empty:
        return 0, 0, 0, 0, 0

    total_bultos = f["Bultos despachados"].sum()
    total_viajes = f["Viajes"].sum()
    total_destinos = f["Destino Agencia concat"].nunique()
    total_capacidad = pd.to_numeric(f["Capacidad 100%"], errors="coerce").fillna(0).sum()

    uso_global = round((total_bultos / total_capacidad * 100), 2) if total_capacidad > 0 else 0
    total_gap = pd.to_numeric(f["Gap a 100%"], errors="coerce").fillna(0).sum()

    return total_bultos, total_viajes, total_destinos, uso_global, total_gap


# =========================================================
# APP
# =========================================================
def main():
    chile_tz = pytz.timezone(ZONA_HORARIA)
    st.session_state["ultima_actualizacion_real"] = datetime.now(chile_tz)

    st.title("📦 MaxCube – Transporte Primaria")
    st.caption("Fuente: GitHub /data/MAXCUBE_Primaria.csv")

    if st.sidebar.button("🔄 Actualizar datos"):
        st.rerun()

    df = cargar_maxcube()

    if df.empty:
        st.warning("El archivo MAXCUBE no contiene registros.")
        return

    # -----------------------------------------
    # SIDEBAR
    # -----------------------------------------
    with st.sidebar:
        st.header("🔎 Filtros")

        modo = st.radio("Periodo", ["Día", "Semana", "Mes"], index=0)

        f = df.copy()

        if modo == "Día":
            fechas_validas = sorted(f["Fecha"].dropna().unique())
            fecha_sel = st.selectbox(
                "Fecha",
                fechas_validas,
                index=len(fechas_validas) - 1 if len(fechas_validas) > 0 else 0
            )
            f = f[f["Fecha"] == fecha_sel]

        elif modo == "Semana":
            semanas_validas = sorted(f["Año-Semana"].dropna().unique())
            semana_sel = st.selectbox(
                "Semana",
                semanas_validas,
                index=len(semanas_validas) - 1 if len(semanas_validas) > 0 else 0
            )
            f = f[f["Año-Semana"] == semana_sel]

        else:
            meses_validos = sorted(f["Mes"].dropna().unique())
            mes_sel = st.selectbox(
                "Mes",
                meses_validos,
                index=len(meses_validos) - 1 if len(meses_validos) > 0 else 0
            )
            f = f[f["Mes"] == mes_sel]

        destinos = sorted(f["Destino Agencia concat"].dropna().astype(str).unique())
        destino_sel = st.multiselect("Destino", destinos)

        proveedores = sorted(f["PROVEEDOR"].dropna().astype(str).unique())
        prov_sel = st.multiselect("Proveedor", proveedores)

        patentes = sorted(
            [p for p in f["Patente rampla"].dropna().astype(str).unique() if p.strip() != ""]
        )
        pat_sel = st.multiselect("Patente rampla", patentes)

        if destino_sel:
            f = f[f["Destino Agencia concat"].isin(destino_sel)]

        if prov_sel:
            f = f[f["PROVEEDOR"].isin(prov_sel)]

        if pat_sel:
            f = f[f["Patente rampla"].isin(pat_sel)]

    # Orden definitivo del filtrado
    f = f.sort_values(
        ["Fecha despacho dt", "Destino Agencia concat", "Bitácora", "Nro carga"],
        ascending=[True, True, True, True]
    )

    # -----------------------------------------
    # KPIS
    # -----------------------------------------
    total_bultos, total_viajes, total_destinos, uso_global, total_gap = metricas_globales(f)

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("📦 Bultos", f"{int(total_bultos):,}".replace(",", "."))
    c2.metric("🚚 Viajes", f"{int(total_viajes):,}".replace(",", "."))
    c3.metric("📍 Destinos", total_destinos)
    c4.metric("📊 Uso global %", f"{uso_global}%")
    c5.metric("📉 Gap total", f"{int(total_gap):,}".replace(",", "."))

    st.divider()

    # -----------------------------------------
    # RESUMEN POR DESTINO (VISUAL PRINCIPAL)
    # -----------------------------------------
    df_dest = resumen_por_destino(f)

    st.subheader("📋 Resumen por destino")
    
    st.data_editor(
        df_dest[["Semáforo", "Destino Agencia concat", "Viajes", "Bultos", "Capacidad", "Uso MaxCube %", "Gap"]],
        use_container_width=True,
        disabled=True,
        height=420,
        key="tabla_resumen_destino"
    )


    # -----------------------------------------
    # ALERTAS AUTOMÁTICAS
    # -----------------------------------------
    st.subheader("🚨 Alertas automáticas")

    criticos = df_dest[df_dest["Uso MaxCube %"] < 90]
    sobrecap = df_dest[df_dest["Gap"] < 0]

    if criticos.empty and sobrecap.empty:
        st.success("✅ No se detectan alertas críticas en el periodo seleccionado.")
    else:
        if not criticos.empty:
            st.error(
                "🔴 Destinos bajo 90% de uso MaxCube: "
                + ", ".join(criticos["Destino Agencia concat"].astype(str).tolist())
            )

        if not sobrecap.empty:
            st.warning(
                "⚠️ Destinos sobre 100% de capacidad: "
                + ", ".join(sobrecap["Destino Agencia concat"].astype(str).tolist())
            )

    # -----------------------------------------
    # RANKING AUTOMÁTICO
    # -----------------------------------------
    st.subheader("🏆 Ranking automático")

    col_r1, col_r2 = st.columns(2)

    with col_r1:
        st.markdown("### 🔻 Top 5 peores destinos")
        ranking_peor = df_dest.sort_values("Uso MaxCube %", ascending=True).head(5)
        
        st.data_editor(
            ranking_peor[["Destino Agencia concat", "Uso MaxCube %", "Gap"]],
            use_container_width=True,
            height=220,
            disabled=True,
            key="ranking_peores"
        )


    with col_r2:
        st.markdown("### 🟢 Top 5 mejores destinos")
        ranking_mejor = df_dest.sort_values("Uso MaxCube %", ascending=False).head(5)
       
        st.data_editor(
            ranking_mejor[["Destino Agencia concat", "Uso MaxCube %", "Gap"]],
            use_container_width=True,
            height=220,
            disabled=True,
            key="ranking_mejores"
        )

    # -----------------------------------------
    # VISUAL 1 - Uso MaxCube % por destino
    # -----------------------------------------
    st.subheader("📊 Uso MaxCube % por destino")

    fig_uso = px.bar(
        df_dest.sort_values("Uso MaxCube %", ascending=True),
        x="Uso MaxCube %",
        y="Destino Agencia concat",
        orientation="h",
        text="Uso MaxCube %",
        color="Uso MaxCube %",
        color_continuous_scale="RdYlGn"
    )

    fig_uso.add_vline(x=100, line_dash="dash", line_color="red", line_width=2)

    fig_uso.update_layout(
        height=600,
        xaxis_title="Uso MaxCube %",
        yaxis_title="Destino",
        coloraxis_showscale=False
    )

    st.plotly_chart(fig_uso, use_container_width=True)

    # -----------------------------------------
    # VISUAL 2 - Gap a 100% por destino
    # -----------------------------------------
    st.subheader("📉 Gap a 100% por destino")

    fig_gap = px.bar(
        df_dest.sort_values("Gap", ascending=True),
        x="Gap",
        y="Destino Agencia concat",
        orientation="h",
        text="Gap"
    )

    fig_gap.add_vline(x=0, line_dash="dash", line_color="black", line_width=1)

    fig_gap.update_layout(
        height=600,
        xaxis_title="Gap a 100% (bultos)",
        yaxis_title="Destino"
    )

    st.plotly_chart(fig_gap, use_container_width=True)

    # -----------------------------------------
    # RESUMEN POR PATENTE (solo si existe)
    # -----------------------------------------
    df_pat = resumen_por_patente(f)

    if not df_pat.empty:
        st.subheader("🚛 Resumen por patente rampla")
        
        st.data_editor(
            df_pat[["Semáforo", "Patente rampla", "Destinos", "Proveedores", "Viajes", "Bultos", "Capacidad", "Uso MaxCube %", "Gap"]],
            use_container_width=True,
            height=350,
            disabled=True,
            key="resumen_patente"
        )


    # -----------------------------------------
    # DETALLE ORDENADO ASCENDENTE
    # -----------------------------------------
    st.subheader("📄 Detalle de despachos (orden ascendente)")

    
    columnas_detalle = [
        "Fecha de despacho",
        "Hora de despacho",
        "Destino Agencia concat",
        "PROVEEDOR",
        "Patente vehículo",   # ✅ NUEVO
        "Patente rampla",
        "Capacidad 100%",
        "Bultos despachados",
        "Uso MaxCube %",
        "Gap a 100%",
        "Bitácora",
        "Nro carga",
    ]


    columnas_detalle = [c for c in columnas_detalle if c in f.columns]

    
    st.data_editor(
        f[columnas_detalle],
        use_container_width=True,
        height=550,
        disabled=True,
        key="detalle_final"
    )


    # -----------------------------------------
    # DESCARGA
    # -----------------------------------------
    st.download_button(
        "⬇️ Descargar CSV filtrado",
        data=f.to_csv(index=False).encode("utf-8"),
        file_name="maxcube_filtrado.csv",
        mime="text/csv"
    )


if __name__ == "__main__":
    main()
