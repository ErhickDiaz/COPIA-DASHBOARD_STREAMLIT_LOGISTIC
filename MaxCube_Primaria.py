import streamlit as st
import pandas as pd
from github import Github
from io import StringIO
from datetime import datetime
import pytz
import plotly.express as px
import plotly.graph_objects as go

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
    "ARICA": 1800,
    "CHILLAN": 1700,
    "CONCEPCION": 1700,
    "COPIAPO": 1750,
    "EL PINAR": 1250,
    "IQUIQUE": 1800,
    "LA SERENA": 1700,
    "LA SERENA / RUTA SOLITARIA 1059 LV": 1750,
    "RUTA SOLITARIA 1059 LV": 1750,
    "LO ESPEJO": 1560,
    "LOS ANDES": 1560,
    "LOS ANGELES": 1700,
    "MELIPILLA": 1700,
    "OSORNO": 1800,
    "OSORNO / PTO MONTT": 1750,
    "PTO MONTT": 1800,
    "PTO MONTT / RUTA SOLITARIA ELPAC": 1800,
    "RUTA SOLITARIA ELPAC": 1800,
    "COPIAPO / LA SERENA": 1750,
    "LOS ANGELES / TEMUCO": 1750,
    "LOS ANGELES / OSORNO": 1750,
    "SAN FERNANDO / TALCA": 1664,
    "CHILLAN / TALCA": 1664,
    "CONCEPCION / TALCA": 1664,
    "CONCEPCION / CHILLAN": 1750,
    "PTO MONTT / VALDIVIA": 1750,
    "VALDIVIA / PTO MONTT": 1750,
    "VALDIVIA / OSORNO": 1750,
    "OSORNO / VALDIVIA": 1750,
    "ANTOFAGASTA / IQUIQUE": 1750,
    "ANTOFAGASTA / ARICA": 1750,
    "ANTOFAGASTA / ARICA / IQUIQUE": 1750,
    "ANTOFAGASTA / TALCA": 1750,
    "CONCEPCION / LOS ANGELES": 1750,
    "CONCEPCION / TEMUCO": 1750,
    "RANCAGUA": 1700,
    "SAN FERNANDO": 1560,
    "TALCA": 1750,
    "TEMUCO": 1750,
    "VALDIVIA": 1800,
    "VINA DEL MAR": 1664,
}

PROVEEDOR_CAP_2200 = "76746317-0/TRAILER LOGISTICS SPA"

# =========================================================
# CAPACIDAD POR PATENTE DE RAMPLA (Solo LO ESPEJO y EL PINAR)
# =========================================================
CAPACIDAD_RAMPLA_ESPEJO_PINAR = {
    "JF4261": 1080,
    "JG4930": 1280,
    "JG5632": 1280,
    "HXDF11": 1280,
    "HXDF12": 1280,
    "PWVW35": 1280,
    "PWVX27": 1280,
    "KYPH94": 1560,
    "KYPH95": 1560,
    "PXJD32": 1560,
    "PXJD33": 1560,
    "PXJD34": 1560,
    "RSBH44": 600,
    "RBSG83": 600,
    "SCZL44": 600,
    "SCZL42": 600,
    "SSSZ55": 600,
    "SSSZ58": 600,
}

DESTINOS_RAMPLA_RULE = {"LO ESPEJO", "EL PINAR"}

# =========================================================
# NORMALIZACION / CAPACIDAD
# =========================================================
def normalizar_destino(destino):
    destino = str(destino).upper().replace("\xa0", " ").strip()
    destino = " ".join(destino.split())
    partes = [p.strip() for p in destino.split("/") if p.strip()]
    return " / ".join(partes)


def obtener_capacidad(destino):
    destino_norm = normalizar_destino(destino)
    if destino_norm in CAPACIDAD_100_DESTINO:
        return CAPACIDAD_100_DESTINO[destino_norm]

    partes = [p.strip() for p in destino_norm.split("/") if p.strip()]
    for i in range(len(partes)):
        rotado = partes[i:] + partes[:i]
        clave = " / ".join(rotado)
        if clave in CAPACIDAD_100_DESTINO:
            return CAPACIDAD_100_DESTINO[clave]
    return None


# =========================================================
# GITHUB
# =========================================================
@st.cache_data(ttl=300, show_spinner=False)
def leer_csv_github(token, repo_name, folder, filename):
    try:
        g = Github(token)
        repo = g.get_repo(repo_name)
        file_content = repo.get_contents(f"{folder}/{filename}")
        csv_string = file_content.decoded_content.decode("utf-8-sig")
        return pd.read_csv(StringIO(csv_string))
    except Exception as e:
        st.error(f"No se pudo cargar {filename} desde GitHub: {e}")
        return pd.DataFrame()


# =========================================================
# SEMANA BIMBO (Jueves a Miercoles)
# =========================================================
def calcular_semana_bimbo(fecha):
    if pd.isna(fecha):
        return None

    año = fecha.year
    primer_dia = pd.Timestamp(f"{año}-01-01")
    offset = (3 - primer_dia.weekday()) % 7
    primer_jueves = primer_dia + pd.Timedelta(days=offset)

    if fecha < primer_jueves:
        año -= 1
        primer_dia = pd.Timestamp(f"{año}-01-01")
        offset = (3 - primer_dia.weekday()) % 7
        primer_jueves = primer_dia + pd.Timedelta(days=offset)

    dias = (fecha - primer_jueves).days
    semana = (dias // 7) + 1
    return f"{año}-S{str(semana).zfill(2)}"


# =========================================================
# CARGA Y ENRIQUECIMIENTO
# =========================================================
def cargar_maxcube():
    df = leer_csv_github(
        GITHUB_TOKEN,
        REPO_NAME,
        GITHUB_FOLDER,
        ARCHIVO_MAXCUBE,
    ).copy()

    if df.empty:
        return df

    df.columns = [c.strip() for c in df.columns]

    columnas_esperadas = [
        "Bitácora", "Nro carga", "Fecha de despacho", "Hora de despacho",
        "Destino Agencia concat", "PROVEEDOR", "Patente vehículo",
        "Viajes", "Bultos despachados", "Bultos empacados",
    ]
    for col in columnas_esperadas:
        if col not in df.columns:
            df[col] = ""

    if "Patente rampla" not in df.columns:
        df["Patente rampla"] = ""

    for columna_patente in ["Patente rampla", "Patente vehículo"]:
        df[columna_patente] = (
            df[columna_patente]
            .fillna("")
            .astype(str)
            .str.replace('="', "", regex=False)
            .str.replace('"', "", regex=False)
            .str.strip()
            .str.upper()
        )

    # Conserva el Nro carga como texto para evitar notacion cientifica o .0.
    df["Nro carga"] = (
        df["Nro carga"]
        .fillna("")
        .astype(str)
        .str.replace('="', "", regex=False)
        .str.replace('"', "", regex=False)
        .str.replace(r"\.0$", "", regex=True)
        .str.strip()
    )

    df["Fecha de despacho"] = pd.to_datetime(
        df["Fecha de despacho"], dayfirst=True, errors="coerce"
    )
    df["Hora de despacho"] = df["Hora de despacho"].fillna("").astype(str).str.strip()

    fecha_texto = df["Fecha de despacho"].dt.strftime("%d/%m/%Y").fillna("")
    df["Fecha despacho dt"] = pd.to_datetime(
        fecha_texto + " " + df["Hora de despacho"],
        dayfirst=True,
        errors="coerce",
    )
    df["Fecha de despacho"] = df["Fecha de despacho"].dt.strftime("%d/%m/%Y")

    df["Bultos despachados"] = pd.to_numeric(
        df["Bultos despachados"], errors="coerce"
    ).fillna(0)
    df["Bultos empacados"] = pd.to_numeric(
        df["Bultos empacados"], errors="coerce"
    ).fillna(0)
    df["Viajes"] = pd.to_numeric(df["Viajes"], errors="coerce").fillna(1)

    df["Fecha"] = df["Fecha despacho dt"].dt.date
    df["Año-Semana"] = df["Fecha despacho dt"].apply(calcular_semana_bimbo)
    df["Mes"] = df["Fecha despacho dt"].dt.strftime("%Y-%m")

    df["Destino Agencia concat"] = (
        df["Destino Agencia concat"]
        .fillna("")
        .astype(str)
        .str.upper()
        .str.replace("\xa0", " ", regex=False)
        .str.strip()
        .str.replace(r"\s+", " ", regex=True)
        .str.replace(r"\s*/\s*", " / ", regex=True)
        .apply(normalizar_destino)
    )

    df["Capacidad 100%"] = df["Destino Agencia concat"].apply(obtener_capacidad)

    # Override rampla, solo LO ESPEJO y EL PINAR.
    mask_destinos = df["Destino Agencia concat"].isin(DESTINOS_RAMPLA_RULE)
    cap_por_rampla = df["Patente rampla"].map(CAPACIDAD_RAMPLA_ESPEJO_PINAR)
    df.loc[
        mask_destinos & cap_por_rampla.notna(),
        "Capacidad 100%",
    ] = cap_por_rampla

    # Override proveedor 2200.
    df.loc[
        df["PROVEEDOR"].fillna("").astype(str).str.strip().str.upper()
        == PROVEEDOR_CAP_2200.upper(),
        "Capacidad 100%",
    ] = 2200

    capacidad = pd.to_numeric(df["Capacidad 100%"], errors="coerce")
    df["Uso MaxCube %"] = (
        df["Bultos despachados"].div(capacidad.where(capacidad > 0)) * 100
    ).round(2)
    df["Gap a 100%"] = capacidad - df["Bultos despachados"]

    df = df.sort_values(
        ["Fecha despacho dt", "Destino Agencia concat", "Bitácora", "Nro carga"],
        ascending=[True, True, True, True],
    )
    return df


# =========================================================
# AUXILIARES
# =========================================================
def semaforo(valor):
    if pd.isna(valor):
        return "⚪"
    if valor < 90:
        return "🔴"
    if valor < 100:
        return "🟠"
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
            Gap=("Gap a 100%", "sum"),
        )
    )
    resumen["Uso MaxCube %"] = (
        resumen["Bultos"].div(resumen["Capacidad"].where(resumen["Capacidad"] > 0)) * 100
    ).round(2)
    resumen["Semáforo"] = resumen["Uso MaxCube %"].apply(semaforo)
    return resumen.sort_values("Uso MaxCube %", ascending=True)


def metricas_globales(f):
    if f.empty:
        return 0, 0, 0, 0, 0

    f_aux = f.copy()
    f_aux["Bultos"] = pd.to_numeric(
        f_aux["Bultos despachados"], errors="coerce"
    ).fillna(0)
    f_aux["Capacidad"] = pd.to_numeric(
        f_aux["Capacidad 100%"], errors="coerce"
    )

    total_bultos = f_aux["Bultos"].sum()
    total_viajes = pd.to_numeric(
        f_aux["Viajes"], errors="coerce"
    ).fillna(0).sum()
    total_destinos = f_aux["Destino Agencia concat"].nunique()

    f_valid = f_aux[
        f_aux["Capacidad"].notna() & (f_aux["Capacidad"] > 0)
    ].copy()

    if f_valid.empty:
        uso_global = 0
    else:
        resumen = f_valid.groupby("Destino Agencia concat").agg(
            Bultos=("Bultos", "sum"),
            Capacidad=("Capacidad", "sum"),
        )
        resumen["Bultos capados"] = resumen[["Bultos", "Capacidad"]].min(axis=1)
        uso_global = round(
            resumen["Bultos capados"].sum()
            / resumen["Capacidad"].sum()
            * 100,
            2,
        )

    total_gap = pd.to_numeric(
        f_aux["Gap a 100%"], errors="coerce"
    ).fillna(0).sum()

    return total_bultos, total_viajes, total_destinos, uso_global, total_gap


# =========================================================
# CAJA 3D
# =========================================================
def numero_seguro(valor):
    numero = pd.to_numeric(valor, errors="coerce")
    return 0.0 if pd.isna(numero) else float(numero)


def crear_caja_3d(registro):
    nro_carga = str(registro.get("Nro carga", "")).strip()
    destino = str(registro.get("Destino Agencia concat", "")).strip()
    bultos = numero_seguro(registro.get("Bultos despachados", 0))
    capacidad = numero_seguro(registro.get("Capacidad 100%", 0))
    uso_real = (bultos / capacidad * 100) if capacidad > 0 else 0
    uso_visual = max(0, min(uso_real, 100))

    # Modelo visual proporcional. No representa ubicacion fisica real de SKU.
    largo, ancho, alto = 12.0, 2.5, 2.7
    largo_ocupado = largo * uso_visual / 100

    fig = go.Figure()

    vertices = [
        (0, 0, 0), (largo, 0, 0), (largo, ancho, 0), (0, ancho, 0),
        (0, 0, alto), (largo, 0, alto), (largo, ancho, alto), (0, ancho, alto),
    ]
    aristas = [
        (0, 1), (1, 2), (2, 3), (3, 0),
        (4, 5), (5, 6), (6, 7), (7, 4),
        (0, 4), (1, 5), (2, 6), (3, 7),
    ]

    for inicio, fin in aristas:
        fig.add_trace(
            go.Scatter3d(
                x=[vertices[inicio][0], vertices[fin][0]],
                y=[vertices[inicio][1], vertices[fin][1]],
                z=[vertices[inicio][2], vertices[fin][2]],
                mode="lines",
                line=dict(color="#37474F", width=5),
                hoverinfo="skip",
                showlegend=False,
            )
        )

    if largo_ocupado > 0:
        color = "#00A651" if uso_real >= 100 else "#F9A825" if uso_real >= 90 else "#D32F2F"
        fig.add_trace(
            go.Mesh3d(
                x=[0, largo_ocupado, largo_ocupado, 0, 0, largo_ocupado, largo_ocupado, 0],
                y=[0, 0, ancho, ancho, 0, 0, ancho, ancho],
                z=[0, 0, 0, 0, alto, alto, alto, alto],
                i=[0, 0, 0, 4, 4, 4, 0, 1, 2, 3, 1, 2],
                j=[1, 2, 3, 5, 6, 7, 4, 5, 6, 7, 5, 6],
                k=[2, 3, 1, 6, 7, 5, 1, 6, 7, 4, 2, 3],
                color=color,
                opacity=0.82,
                hovertemplate=(
                    f"Carga: {nro_carga}<br>"
                    f"Destino: {destino}<br>"
                    f"Bultos: {bultos:,.0f}<br>"
                    f"Capacidad: {capacidad:,.0f}<br>"
                    f"Uso MaxCube: {uso_real:.2f}%"
                    "<extra></extra>"
                ),
                showlegend=False,
            )
        )

    fig.update_layout(
        title=f"Carga {nro_carga} | Ocupación {uso_real:.2f}%",
        height=620,
        margin=dict(l=0, r=0, t=55, b=0),
        scene=dict(
            xaxis=dict(title="Largo", showticklabels=False, range=[0, largo]),
            yaxis=dict(title="Ancho", showticklabels=False, range=[0, ancho]),
            zaxis=dict(title="Altura", showticklabels=False, range=[0, alto]),
            aspectmode="manual",
            aspectratio=dict(x=2.8, y=1, z=1),
            camera=dict(eye=dict(x=1.6, y=1.6, z=1.15)),
        ),
        showlegend=False,
    )
    return fig


def mostrar_detalle_y_caja_3d(f, columnas_detalle):
    tabla = f[columnas_detalle].reset_index(drop=True).copy()

    evento = st.dataframe(
        tabla,
        use_container_width=True,
        height=550,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        key="detalle_final_seleccionable",
        column_config={
            "Nro carga": st.column_config.TextColumn(
                "Nro carga",
                help="Selecciona la fila de la carga para desplegar su Caja 3D.",
            ),
            "Uso MaxCube %": st.column_config.NumberColumn(
                "Uso MaxCube %",
                format="%.2f%%",
            ),
        },
    )

    filas_seleccionadas = evento.selection.rows
    if not filas_seleccionadas:
        st.info("Selecciona una fila de la tabla para desplegar la Caja 3D de su Nro. de carga.")
        return

    posicion = filas_seleccionadas[0]
    registro = tabla.iloc[posicion].copy()
    nro_carga = str(registro.get("Nro carga", "")).strip()

    bultos = numero_seguro(registro.get("Bultos despachados", 0))
    empacados = numero_seguro(registro.get("Bultos empacados", 0))
    capacidad = numero_seguro(registro.get("Capacidad 100%", 0))
    uso = round(bultos / capacidad * 100, 2) if capacidad > 0 else 0

    st.subheader(f"📦 Caja 3D de la carga {nro_carga}")
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Carga", nro_carga or "Sin número")
    k2.metric("Despachados", f"{int(bultos):,}".replace(",", "."))
    k3.metric("Empacados", f"{int(empacados):,}".replace(",", "."))
    k4.metric("Capacidad", f"{int(capacidad):,}".replace(",", "."))
    k5.metric("Uso MaxCube", f"{uso:.2f}%")

    st.plotly_chart(
        crear_caja_3d(registro),
        use_container_width=True,
        key=f"caja_3d_{posicion}_{nro_carga}",
    )
    st.caption(
        "La Caja 3D representa proporcionalmente Bultos despachados / Capacidad 100%. "
        "La distribución física por SKU se incorporará cuando el detalle dimensional esté disponible."
    )


# =========================================================
# APP
# =========================================================
def main():
    chile_tz = pytz.timezone(ZONA_HORARIA)
    st.session_state["ultima_actualizacion_real"] = datetime.now(chile_tz)

    st.title("📦 MaxCube – Transporte Primaria")
    st.caption("Fuente: GitHub /data/MAXCUBE_Primaria.csv")

    if st.sidebar.button("🔄 Actualizar datos"):
        leer_csv_github.clear()
        st.rerun()

    df = cargar_maxcube()

    if df.empty:
        st.warning("El archivo MAXCUBE no contiene registros.")
        return

    with st.sidebar:
        st.header("🔎 Filtros")
        modo = st.radio("Periodo", ["Día", "Semana", "Mes"], index=0)
        f = df.copy()

        if modo == "Día":
            fechas_validas = sorted(f["Fecha"].dropna().unique())
            if not fechas_validas:
                st.warning("No hay fechas válidas para filtrar.")
                return
            fecha_sel = st.selectbox("Fecha", fechas_validas, index=len(fechas_validas) - 1)
            f = f[f["Fecha"] == fecha_sel]

        elif modo == "Semana":
            semanas_validas = sorted(f["Año-Semana"].dropna().unique())
            if not semanas_validas:
                st.warning("No hay semanas válidas para filtrar.")
                return
            semana_sel = st.selectbox("Semana", semanas_validas, index=len(semanas_validas) - 1)
            f = f[f["Año-Semana"] == semana_sel]

        else:
            meses_validos = sorted(f["Mes"].dropna().unique())
            if not meses_validos:
                st.warning("No hay meses válidos para filtrar.")
                return
            mes_sel = st.selectbox("Mes", meses_validos, index=len(meses_validos) - 1)
            f = f[f["Mes"] == mes_sel]

        destinos = sorted(f["Destino Agencia concat"].dropna().astype(str).unique())
        destino_sel = st.multiselect("Destino", destinos)

        proveedores = sorted(f["PROVEEDOR"].dropna().astype(str).unique())
        prov_sel = st.multiselect("Proveedor", proveedores)

        patentes_vehiculo = sorted(
            p for p in f["Patente vehículo"].dropna().astype(str).unique() if p.strip()
        )
        pat_veh_sel = st.multiselect("Patente vehículo", patentes_vehiculo)

        patentes = sorted(
            p for p in f["Patente rampla"].dropna().astype(str).unique() if p.strip()
        )
        pat_sel = st.multiselect("Patente rampla", patentes)

        if destino_sel:
            f = f[f["Destino Agencia concat"].isin(destino_sel)]
        if prov_sel:
            f = f[f["PROVEEDOR"].isin(prov_sel)]
        if pat_veh_sel:
            f = f[f["Patente vehículo"].isin(pat_veh_sel)]
        if pat_sel:
            f = f[f["Patente rampla"].isin(pat_sel)]

    f = f.sort_values(
        ["Fecha despacho dt", "Destino Agencia concat", "Bitácora", "Nro carga"],
        ascending=[True, True, True, True],
    )

    if f.empty:
        st.warning("No hay registros para los filtros seleccionados.")
        return

    total_bultos, total_viajes, total_destinos, uso_global, total_gap = metricas_globales(f)
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("📦 Bultos", f"{int(total_bultos):,}".replace(",", "."))
    c2.metric("🚚 Viajes", f"{int(total_viajes):,}".replace(",", "."))
    c3.metric("📍 Destinos", total_destinos)
    c4.metric("📊 Uso global %", f"{uso_global}%")
    c5.metric("📉 Gap total", f"{int(total_gap):,}".replace(",", "."))

    st.divider()

    df_dest = resumen_por_destino(f)
    st.subheader("📋 Resumen por destino")
    st.data_editor(
        df_dest[[
            "Semáforo", "Destino Agencia concat", "Viajes", "Bultos",
            "Capacidad", "Uso MaxCube %", "Gap",
        ]],
        use_container_width=True,
        disabled=True,
        height=420,
        key="tabla_resumen_destino",
    )

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

    st.subheader("🏆 Ranking automático")
    col_r1, col_r2 = st.columns(2)

    with col_r1:
        st.markdown("### 🔻 Top 5 peores destinos")
        st.data_editor(
            df_dest.sort_values("Uso MaxCube %", ascending=True)
            .head(5)[["Destino Agencia concat", "Uso MaxCube %", "Gap"]],
            use_container_width=True,
            height=220,
            disabled=True,
            key="ranking_peores",
        )

    with col_r2:
        st.markdown("### 🟢 Top 5 mejores destinos")
        st.data_editor(
            df_dest.sort_values("Uso MaxCube %", ascending=False)
            .head(5)[["Destino Agencia concat", "Uso MaxCube %", "Gap"]],
            use_container_width=True,
            height=220,
            disabled=True,
            key="ranking_mejores",
        )

    st.subheader("📊 Uso MaxCube % por destino")
    fig_uso = px.bar(
        df_dest.sort_values("Uso MaxCube %", ascending=True),
        x="Uso MaxCube %",
        y="Destino Agencia concat",
        orientation="h",
        text="Uso MaxCube %",
        color="Uso MaxCube %",
        color_continuous_scale="RdYlGn",
    )
    fig_uso.add_vline(x=100, line_dash="dash", line_color="red", line_width=2)
    fig_uso.update_layout(
        height=600,
        xaxis_title="Uso MaxCube %",
        yaxis_title="Destino",
        coloraxis_showscale=False,
    )
    st.plotly_chart(fig_uso, use_container_width=True)

    st.subheader("📉 Gap a 100% por destino")
    fig_gap = px.bar(
        df_dest.sort_values("Gap", ascending=True),
        x="Gap",
        y="Destino Agencia concat",
        orientation="h",
        text="Gap",
    )
    fig_gap.add_vline(x=0, line_dash="dash", line_color="black", line_width=1)
    fig_gap.update_layout(
        height=600,
        xaxis_title="Gap a 100% (bultos)",
        yaxis_title="Destino",
    )
    st.plotly_chart(fig_gap, use_container_width=True)

    st.subheader("📄 Detalle de despachos (selecciona una carga)")
    columnas_detalle = [
        "Fecha de despacho", "Hora de despacho", "Destino Agencia concat", "PROVEEDOR",
        "Patente vehículo", "Patente rampla", "Capacidad 100%",
        "Bultos despachados", "Bultos empacados",
        "Uso MaxCube %", "Gap a 100%", "Bitácora", "Nro carga",
    ]
    columnas_detalle = [c for c in columnas_detalle if c in f.columns]
    mostrar_detalle_y_caja_3d(f, columnas_detalle)

    st.download_button(
        "⬇️ Descargar CSV filtrado",
        data=f.to_csv(index=False).encode("utf-8"),
        file_name="maxcube_filtrado.csv",
        mime="text/csv",
    )


if __name__ == "__main__":
    main()
