import re
import unicodedata
from datetime import datetime
from io import StringIO

import pandas as pd
import plotly.express as px
import pytz
import streamlit as st
from github import Github

# =========================================================
# CONFIG
# =========================================================
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
REPO_NAME = "ErhickDiaz/COPIA-DASHBOARD_STREAMLIT_LOGISTIC"
GITHUB_FOLDER = "data"
ARCHIVO_COSTO_SERVIR = "Costo_por_Servir_T1.csv"
ZONA_HORARIA = "America/Santiago"

# =========================================================
# GITHUB
# =========================================================
def leer_csv_github(repo, filename):
    try:
        archivo = repo.get_contents(f"{GITHUB_FOLDER}/{filename}")
        contenido = archivo.decoded_content.decode("utf-8-sig")

        # Detecta coma o punto y coma.
        primera_linea = contenido.splitlines()[0] if contenido.splitlines() else ""
        separador = ";" if primera_linea.count(";") > primera_linea.count(",") else ","

        return pd.read_csv(
            StringIO(contenido),
            sep=separador,
            engine="python",
        )
    except Exception as e:
        st.error(f"No se pudo cargar {filename} desde GitHub: {e}")
        return pd.DataFrame()


# =========================================================
# NORMALIZACION
# =========================================================
def normalizar_texto(valor):
    texto = str(valor).strip().lower()
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", " ", texto).strip()


def buscar_columna(df, opciones, obligatoria=True):
    columnas = {normalizar_texto(c): c for c in df.columns}

    # Primero coincidencia exacta normalizada.
    for opcion in opciones:
        clave = normalizar_texto(opcion)
        if clave in columnas:
            return columnas[clave]

    # Después coincidencia parcial.
    for clave, original in columnas.items():
        for opcion in opciones:
            if normalizar_texto(opcion) in clave:
                return original

    if obligatoria:
        raise KeyError(
            f"No se encontró una columna equivalente a {opciones}. "
            f"Columnas disponibles: {list(df.columns)}"
        )
    return None


def limpiar_identificador(serie):
    return (
        serie.fillna("")
        .astype(str)
        .str.replace('="', "", regex=False)
        .str.replace('"', "", regex=False)
        .str.replace(r"\.0$", "", regex=True)
        .str.strip()
    )


def convertir_numero(serie):
    if pd.api.types.is_numeric_dtype(serie):
        return pd.to_numeric(serie, errors="coerce").fillna(0.0)

    limpio = (
        serie.fillna("")
        .astype(str)
        .str.replace('="', "", regex=False)
        .str.replace('"', "", regex=False)
        .str.replace("$", "", regex=False)
        .str.replace(" ", "", regex=False)
    )

    # Formato habitual chileno: 1.234.567 o 1234567,89.
    contiene_coma = limpio.str.contains(",", regex=False)
    limpio.loc[contiene_coma] = (
        limpio.loc[contiene_coma]
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False)
    )

    return pd.to_numeric(limpio, errors="coerce").fillna(0.0)


def formato_clp(valor):
    return f"$ {float(valor):,.0f}".replace(",", ".")


def calcular_semana_bimbo(fecha):
    if pd.isna(fecha):
        return None

    anio = fecha.year
    primer_dia = pd.Timestamp(f"{anio}-01-01")
    offset = (3 - primer_dia.weekday()) % 7
    primer_jueves = primer_dia + pd.Timedelta(days=offset)

    if fecha < primer_jueves:
        anio -= 1
        primer_dia = pd.Timestamp(f"{anio}-01-01")
        offset = (3 - primer_dia.weekday()) % 7
        primer_jueves = primer_dia + pd.Timedelta(days=offset)

    semana = ((fecha - primer_jueves).days // 7) + 1
    return f"{anio}-S{str(semana).zfill(2)}"


# =========================================================
# CARGA Y ENRIQUECIMIENTO
# =========================================================
def cargar_costo_por_servir():
    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(REPO_NAME)
    bruto = leer_csv_github(repo, ARCHIVO_COSTO_SERVIR)

    if bruto.empty:
        return bruto

    bruto.columns = [str(c).strip() for c in bruto.columns]

    try:
        c_fecha = buscar_columna(bruto, ["Fecha", "Fecha de despacho"])
        c_hora = buscar_columna(bruto, ["Hora", "Hora de despacho"], obligatoria=False)
        c_destino = buscar_columna(bruto, ["Destino", "Destino Agencia concat"])
        c_proveedor = buscar_columna(bruto, ["Proveedor", "PROVEEDOR"])
        c_flete = buscar_columna(bruto, ["Valor Flete", "Flete COSTO AC", "Costo Flete"])
        c_bdesp = buscar_columna(bruto, ["Bultos despachados"])
        c_vdesp = buscar_columna(
            bruto,
            ["Costo de los bultos despachados", "Valor despachado"],
        )
        c_bemp = buscar_columna(bruto, ["Bultos empacados"])
        c_vemp = buscar_columna(
            bruto,
            ["Costo de los bultos empacados", "Valor empacado"],
        )
        c_bitacora = buscar_columna(bruto, ["Bitacora", "Bitácora"])
        c_carga = buscar_columna(bruto, ["Nro carga", "Nro de Carga", "Numero carga"])
    except KeyError as e:
        st.error(str(e))
        return pd.DataFrame()

    df = pd.DataFrame()
    df["Fecha despacho dt"] = pd.to_datetime(
        bruto[c_fecha], dayfirst=True, errors="coerce"
    )
    df["Fecha de despacho"] = df["Fecha despacho dt"].dt.strftime("%d/%m/%Y")
    df["Hora de despacho"] = (
        bruto[c_hora].fillna("").astype(str).str.strip()
        if c_hora
        else ""
    )
    df["Destino"] = (
        bruto[c_destino].fillna("SIN DESTINO").astype(str).str.upper().str.strip()
    )
    df["Proveedor"] = (
        bruto[c_proveedor].fillna("SIN PROVEEDOR").astype(str).str.upper().str.strip()
    )
    df["Valor Flete"] = convertir_numero(bruto[c_flete])
    df["Bultos despachados"] = convertir_numero(bruto[c_bdesp])
    df["Valor despachado"] = convertir_numero(bruto[c_vdesp])
    df["Bultos empacados"] = convertir_numero(bruto[c_bemp])
    df["Valor empacado"] = convertir_numero(bruto[c_vemp])
    df["Bitácora"] = limpiar_identificador(bruto[c_bitacora])
    df["Nro carga"] = limpiar_identificador(bruto[c_carga])

    df["Fecha"] = df["Fecha despacho dt"].dt.date
    df["Año-Semana"] = df["Fecha despacho dt"].apply(calcular_semana_bimbo)
    df["Mes"] = df["Fecha despacho dt"].dt.strftime("%Y-%m")
    df["Diferencia bultos"] = (
        df["Bultos despachados"] - df["Bultos empacados"]
    )

    df["CxQ"] = 0.0
    mask_valor = df["Valor empacado"] > 0
    df.loc[mask_valor, "CxQ"] = (
        df.loc[mask_valor, "Valor Flete"]
        / df.loc[mask_valor, "Valor empacado"]
    )

    df["Estado cruce"] = df["Valor Flete"].gt(0).map(
        {True: "Flete cruzado", False: "Sin COSTO AC"}
    )

    return df.sort_values(
        ["Fecha despacho dt", "Destino", "Bitácora", "Nro carga"],
        ascending=[True, True, True, True],
    )


# =========================================================
# RESUMENES
# =========================================================
def resumen_destino(df):
    if df.empty:
        return pd.DataFrame()

    r = (
        df.groupby("Destino", as_index=False)
        .agg(
            Viajes=("Nro carga", "count"),
            Flete=("Valor Flete", "sum"),
            Valor_empacado=("Valor empacado", "sum"),
            Bultos=("Bultos empacados", "sum"),
            Cargas_con_flete=("Valor Flete", lambda s: int((s > 0).sum())),
        )
    )
    r["CxQ"] = 0.0
    mask = r["Valor_empacado"] > 0
    r.loc[mask, "CxQ"] = r.loc[mask, "Flete"] / r.loc[mask, "Valor_empacado"]
    r["Cobertura flete %"] = (
        r["Cargas_con_flete"] / r["Viajes"] * 100
    ).round(1)
    return r.sort_values("CxQ", ascending=False)


def resumen_proveedor(df):
    if df.empty:
        return pd.DataFrame()

    r = (
        df.groupby("Proveedor", as_index=False)
        .agg(
            Viajes=("Nro carga", "count"),
            Flete=("Valor Flete", "sum"),
            Valor_empacado=("Valor empacado", "sum"),
        )
    )
    r["CxQ"] = 0.0
    mask = r["Valor_empacado"] > 0
    r.loc[mask, "CxQ"] = r.loc[mask, "Flete"] / r.loc[mask, "Valor_empacado"]
    return r.sort_values("Flete", ascending=False)


# =========================================================
# APP
# =========================================================
def main():
    chile_tz = pytz.timezone(ZONA_HORARIA)
    st.session_state["ultima_actualizacion_real"] = datetime.now(chile_tz)

    st.title("💰 Costo por Servir T1")
    st.caption(
        "Fuente: GitHub /data/Costo_por_Servir_T1.csv · "
        "Flete cruzado por Nro carga desde VIAJES WMS, COSTO columna AC"
    )

    if st.sidebar.button("🔄 Actualizar datos", key="actualizar_costo_servir"):
        st.rerun()

    df = cargar_costo_por_servir()

    if df.empty:
        st.warning("El archivo Costo_por_Servir_T1.csv no contiene registros válidos.")
        return

    # SIDEBAR: misma lógica Día / Semana / Mes de MaxCube.
    with st.sidebar:
        st.header("🔎 Filtros Costo por Servir")
        modo = st.radio(
            "Periodo",
            ["Día", "Semana", "Mes"],
            index=0,
            key="cps_periodo",
        )
        f = df.copy()

        if modo == "Día":
            fechas = sorted(f["Fecha"].dropna().unique())
            if fechas:
                fecha_sel = st.selectbox(
                    "Fecha",
                    fechas,
                    index=len(fechas) - 1,
                    key="cps_fecha",
                )
                f = f[f["Fecha"] == fecha_sel]

        elif modo == "Semana":
            semanas = sorted(f["Año-Semana"].dropna().unique())
            if semanas:
                semana_sel = st.selectbox(
                    "Semana",
                    semanas,
                    index=len(semanas) - 1,
                    key="cps_semana",
                )
                f = f[f["Año-Semana"] == semana_sel]

        else:
            meses = sorted(f["Mes"].dropna().unique())
            if meses:
                mes_sel = st.selectbox(
                    "Mes",
                    meses,
                    index=len(meses) - 1,
                    key="cps_mes",
                )
                f = f[f["Mes"] == mes_sel]

        destinos = sorted(f["Destino"].dropna().astype(str).unique())
        destino_sel = st.multiselect("Destino", destinos, key="cps_destino")

        proveedores = sorted(f["Proveedor"].dropna().astype(str).unique())
        proveedor_sel = st.multiselect(
            "Proveedor", proveedores, key="cps_proveedor"
        )

        estado_sel = st.selectbox(
            "Cruce de flete",
            ["Todos", "Flete cruzado", "Sin COSTO AC"],
            key="cps_estado",
        )

        busqueda = st.text_input(
            "Buscar carga o bitácora",
            key="cps_busqueda",
        ).strip()

        if destino_sel:
            f = f[f["Destino"].isin(destino_sel)]
        if proveedor_sel:
            f = f[f["Proveedor"].isin(proveedor_sel)]
        if estado_sel != "Todos":
            f = f[f["Estado cruce"] == estado_sel]
        if busqueda:
            q = busqueda.lower()
            f = f[
                f["Nro carga"].str.lower().str.contains(q, na=False, regex=False)
                | f["Bitácora"].str.lower().str.contains(q, na=False, regex=False)
            ]

    f = f.sort_values(
        ["Fecha despacho dt", "Destino", "Bitácora", "Nro carga"],
        ascending=[True, True, True, True],
    )

    # KPIs ponderados.
    total_viajes = len(f)
    total_valor = f["Valor empacado"].sum()
    total_flete = f["Valor Flete"].sum()
    total_bultos = f["Bultos empacados"].sum()
    total_con_flete = int((f["Valor Flete"] > 0).sum())
    cxq_global = total_flete / total_valor if total_valor > 0 else 0
    cobertura = total_con_flete / total_viajes if total_viajes else 0

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("🚚 Viajes", f"{total_viajes:,}".replace(",", "."))
    c2.metric("📦 Bultos empacados", f"{int(total_bultos):,}".replace(",", "."))
    c3.metric("💵 Valor empacado", formato_clp(total_valor))
    c4.metric("🧾 Flete AC", formato_clp(total_flete))
    c5.metric("📊 CxQ global", f"{cxq_global:.2%}" if total_valor > 0 else "Pendiente")
    c6.metric("🔗 Cobertura flete", f"{cobertura:.1%}")

    st.divider()

    # Resumen por destino.
    df_dest = resumen_destino(f)
    st.subheader("📋 Resumen por destino")
    if not df_dest.empty:
        tabla_dest = df_dest.copy()
        tabla_dest["Flete"] = tabla_dest["Flete"].map(formato_clp)
        tabla_dest["Valor empacado"] = tabla_dest["Valor_empacado"].map(formato_clp)
        tabla_dest["CxQ %"] = tabla_dest["CxQ"].map(lambda x: round(x * 100, 2))
        st.data_editor(
            tabla_dest[
                [
                    "Destino", "Viajes", "Bultos", "Flete",
                    "Valor empacado", "CxQ %", "Cobertura flete %",
                ]
            ],
            use_container_width=True,
            disabled=True,
            height=420,
            key="cps_resumen_destino",
        )

    # Alertas de calidad del cruce.
    st.subheader("🚨 Alertas automáticas")
    sin_flete = f[f["Valor Flete"] <= 0]
    sin_valor = f[f["Valor empacado"] <= 0]
    diferencia = f[f["Diferencia bultos"] != 0]

    if sin_flete.empty and sin_valor.empty and diferencia.empty:
        st.success("✅ Todos los viajes visibles están conciliados.")
    else:
        if not sin_flete.empty:
            st.error(f"🔴 {len(sin_flete)} viaje(s) sin COSTO AC cruzado.")
        if not sin_valor.empty:
            st.warning(f"🟠 {len(sin_valor)} viaje(s) sin valor empacado.")
        if not diferencia.empty:
            st.warning(
                f"🟠 {len(diferencia)} viaje(s) con diferencia entre bultos "
                "despachados y empacados."
            )

    # Ranking.
    st.subheader("🏆 Ranking automático")
    col_r1, col_r2 = st.columns(2)
    with col_r1:
        st.markdown("### 🔺 Top 5 mayor CxQ")
        top_cxq = df_dest[df_dest["Valor_empacado"] > 0].head(5).copy()
        top_cxq["CxQ %"] = (top_cxq["CxQ"] * 100).round(2)
        st.data_editor(
            top_cxq[["Destino", "Viajes", "CxQ %"]],
            use_container_width=True,
            disabled=True,
            height=220,
            key="cps_ranking_cxq",
        )

    with col_r2:
        st.markdown("### 💵 Top 5 mayor flete")
        top_flete = df_dest.sort_values("Flete", ascending=False).head(5).copy()
        top_flete["Flete CLP"] = top_flete["Flete"].map(formato_clp)
        st.data_editor(
            top_flete[["Destino", "Viajes", "Flete CLP"]],
            use_container_width=True,
            disabled=True,
            height=220,
            key="cps_ranking_flete",
        )

    # Visuales.
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        st.subheader("📊 CxQ por destino")
        graf_dest = df_dest[df_dest["Valor_empacado"] > 0].copy()
        fig_dest = px.bar(
            graf_dest.sort_values("CxQ", ascending=True),
            x="CxQ",
            y="Destino",
            orientation="h",
            text_auto=".2%",
            color="CxQ",
            color_continuous_scale="RdYlGn_r",
        )
        fig_dest.update_xaxes(tickformat=".1%")
        fig_dest.update_layout(
            height=560,
            xaxis_title="Costo por Servir",
            yaxis_title="Destino",
            coloraxis_showscale=False,
        )
        st.plotly_chart(fig_dest, use_container_width=True)

    with col_g2:
        st.subheader("💵 Flete por proveedor")
        df_prov = resumen_proveedor(f)
        fig_prov = px.bar(
            df_prov.sort_values("Flete", ascending=True),
            x="Flete",
            y="Proveedor",
            orientation="h",
            color="CxQ",
            color_continuous_scale="Tealgrn",
        )
        fig_prov.update_layout(
            height=560,
            xaxis_title="Flete CLP",
            yaxis_title="Proveedor",
            coloraxis_colorbar_title="CxQ",
        )
        st.plotly_chart(fig_prov, use_container_width=True)

    # Detalle.
    st.subheader("📄 Detalle de viajes")
    detalle = f.copy()
    detalle["CxQ %"] = (detalle["CxQ"] * 100).round(2)

    columnas_detalle = [
        "Fecha de despacho", "Hora de despacho", "Destino", "Proveedor",
        "Valor Flete", "Bultos despachados", "Valor despachado",
        "Bultos empacados", "Valor empacado", "CxQ %", "Bitácora",
        "Nro carga", "Estado cruce",
    ]

    st.data_editor(
        detalle[columnas_detalle],
        use_container_width=True,
        height=550,
        disabled=True,
        key="cps_detalle_final",
        column_config={
            "Valor Flete": st.column_config.NumberColumn(
                "Valor Flete", format="$ %d"
            ),
            "Valor despachado": st.column_config.NumberColumn(
                "Valor despachado", format="$ %d"
            ),
            "Valor empacado": st.column_config.NumberColumn(
                "Valor empacado", format="$ %d"
            ),
            "CxQ %": st.column_config.NumberColumn("CxQ %", format="%.2f %%"),
            "Nro carga": st.column_config.TextColumn("Nro carga", width="large"),
            "Proveedor": st.column_config.TextColumn("Proveedor", width="large"),
        },
    )

    st.download_button(
        "⬇️ Descargar CSV filtrado",
        data=f.to_csv(index=False).encode("utf-8-sig"),
        file_name="Costo_por_Servir_T1_filtrado.csv",
        mime="text/csv",
        key="cps_descarga",
    )


if __name__ == "__main__":
    main()
