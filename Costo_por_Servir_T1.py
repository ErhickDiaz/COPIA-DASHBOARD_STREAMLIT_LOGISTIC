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
ARCHIVO_COSTO_FLETE = "viajes primaria.csv"
ZONA_HORARIA = "America/Santiago"


# =========================================================
# GITHUB
# =========================================================
def obtener_repo():
    return Github(GITHUB_TOKEN).get_repo(REPO_NAME)


def leer_csv_github(repo, filename):
    try:
        archivo = repo.get_contents(f"{GITHUB_FOLDER}/{filename}")
        contenido = archivo.decoded_content.decode("utf-8-sig")

        lineas = contenido.splitlines()
        primera_linea = lineas[0] if lineas else ""
        separador = ";" if primera_linea.count(";") > primera_linea.count(",") else ","

        return pd.read_csv(
            StringIO(contenido),
            sep=separador,
            engine="python",
            dtype=str,
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
    mapa = {normalizar_texto(c): c for c in df.columns}

    for opcion in opciones:
        clave = normalizar_texto(opcion)
        if clave in mapa:
            return mapa[clave]

    for clave, original in mapa.items():
        for opcion in opciones:
            if normalizar_texto(opcion) in clave:
                return original

    if obligatoria:
        raise KeyError(
            f"No se encontro una columna equivalente a {opciones}. "
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
        .str.replace("\u00a0", " ", regex=False)
        .str.strip()
        .str.upper()
    )


def convertir_numero(serie):
    if pd.api.types.is_numeric_dtype(serie):
        return pd.to_numeric(
            serie,
            errors="coerce"
        ).fillna(0.0)

    limpio = (
        serie.fillna("")
        .astype(str)
        .str.replace('="', "", regex=False)
        .str.replace('"', "", regex=False)
        .str.replace("$", "", regex=False)
        .str.replace("CLP", "", regex=False)
        .str.replace(" ", "", regex=False)
        .str.strip()
    )

    def convertir_valor(valor):
        if valor is None:
            return 0.0

        valor = str(valor).strip()

        if valor == "" or valor.lower() in {
            "nan",
            "none",
            "null",
            "-"
        }:
            return 0.0

        try:
            # Formato chileno con coma decimal:
            # 1.234.567,89
            if "," in valor:
                valor = (
                    valor
                    .replace(".", "")
                    .replace(",", ".")
                )
                return float(valor)

            # Un punto seguido de exactamente tres cifras:
            # 844.268 -> 844268
            if re.fullmatch(r"-?\d{1,3}(\.\d{3})+", valor):
                return float(valor.replace(".", ""))

            # Varios puntos como separadores de miles:
            # 1.234.567
            if valor.count(".") > 1:
                return float(valor.replace(".", ""))

            # Número normal:
            # 844268
            # 844268.50
            return float(valor)

        except (ValueError, TypeError):
            return 0.0

    return limpio.apply(convertir_valor)


def formato_entero(valor):
    return f"{float(valor):,.0f}".replace(",", ".")


def formato_clp(valor):
    return f"$ {formato_entero(valor)}"


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
# COSTO FLETE T1
# Prioridad: Nro de Carga. Respaldo: Bitacora.
# =========================================================
def cargar_costos_flete(repo):
    bruto = leer_csv_github(repo, ARCHIVO_COSTO_FLETE)
    if bruto.empty:
        return bruto

    bruto.columns = [str(c).strip() for c in bruto.columns]

    try:
        c_carga = buscar_columna(
            bruto,
            ["Nro de Carga", "Nro carga", "Numero de Carga", "Numero carga"],
            obligatoria=False,
        )
        c_bitacora = buscar_columna(
            bruto,
            ["Bitacora", "Bitácora", "Numero Bitacora", "Nro Bitacora"],
            obligatoria=False,
        )
        c_costo = buscar_columna(
            bruto,
            ["COSTO", "COSTOS", "Costo Flete", "Valor Flete", "Flete"],
        )
    except KeyError as e:
        st.error(f"Error en {ARCHIVO_COSTO_FLETE}: {e}")
        return pd.DataFrame()

    if not c_carga and not c_bitacora:
        st.error(
            f"{ARCHIVO_COSTO_FLETE} no contiene Nro de Carga ni Bitacora."
        )
        return pd.DataFrame()

    costos = pd.DataFrame(index=bruto.index)
    costos["Nro carga"] = (
        limpiar_identificador(bruto[c_carga]) if c_carga else ""
    )
    costos["Bitacora"] = (
        limpiar_identificador(bruto[c_bitacora]) if c_bitacora else ""
    )
    costos["COSTO"] = convertir_numero(bruto[c_costo])

    # Se descartan filas sin costo positivo. Si hay duplicados idénticos,
    # se conserva la ultima aparicion para evitar multiplicar el flete.
    costos = costos[costos["COSTO"] > 0].copy()
    return costos


def crear_mapa_unico(costos, clave):
    if costos.empty or clave not in costos.columns:
        return {}

    validos = costos[costos[clave].astype(str).str.strip().ne("")].copy()
    if validos.empty:
        return {}

    return (
        validos.drop_duplicates(subset=[clave], keep="last")
        .set_index(clave)["COSTO"]
        .to_dict()
    )


def aplicar_costos_flete(df, costos):
    salida = df.copy()

    mapa_carga = crear_mapa_unico(costos, "Nro carga")
    mapa_bitacora = crear_mapa_unico(costos, "Bitacora")

    costo_por_carga = salida["Nro carga"].map(mapa_carga)
    costo_por_bitacora = salida["Bitacora clave"].map(mapa_bitacora)

    salida["Valor Flete"] = costo_por_carga
    salida["Origen Flete"] = "Sin coincidencia"

    encontro_carga = costo_por_carga.notna()
    salida.loc[encontro_carga, "Origen Flete"] = "Nro de Carga"

    # Respaldo solo donde no se encontro la carga.
    usar_bitacora = salida["Valor Flete"].isna() & costo_por_bitacora.notna()
    salida.loc[usar_bitacora, "Valor Flete"] = costo_por_bitacora.loc[usar_bitacora]
    salida.loc[usar_bitacora, "Origen Flete"] = "Bitacora"

    salida["Valor Flete"] = pd.to_numeric(
        salida["Valor Flete"], errors="coerce"
    ).fillna(0.0)

    return salida


# =========================================================
# CARGA Y ENRIQUECIMIENTO DEL CONSOLIDADO
# =========================================================
def cargar_costo_por_servir():
    repo = obtener_repo()
    bruto = leer_csv_github(repo, ARCHIVO_COSTO_SERVIR)

    if bruto.empty:
        return bruto

    bruto.columns = [str(c).strip() for c in bruto.columns]

    try:
        c_fecha = buscar_columna(bruto, ["Fecha", "Fecha de despacho"])
        c_hora = buscar_columna(bruto, ["Hora", "Hora de despacho"], False)
        c_destino = buscar_columna(bruto, ["Destino", "Destino Agencia concat"])
        c_proveedor = buscar_columna(bruto, ["Proveedor", "PROVEEDOR"])
        c_bdesp = buscar_columna(bruto, ["Bultos despachados"])
        c_vdesp = buscar_columna(
            bruto, ["Costo de los bultos despachados", "Valor despachado"]
        )
        c_bemp = buscar_columna(bruto, ["Bultos empacados"])
        c_vemp = buscar_columna(
            bruto, ["Costo de los bultos empacados", "Valor empacado"]
        )
        c_bitacora = buscar_columna(bruto, ["Bitacora", "Bitácora"])
        c_carga = buscar_columna(
            bruto, ["Nro carga", "Nro de Carga", "Numero carga"]
        )
    except KeyError as e:
        st.error(str(e))
        return pd.DataFrame()

    df = pd.DataFrame(index=bruto.index)
    df["Fecha despacho dt"] = pd.to_datetime(
        bruto[c_fecha], dayfirst=True, errors="coerce"
    )
    df["Fecha de despacho"] = df["Fecha despacho dt"].dt.strftime("%d/%m/%Y")
    df["Hora de despacho"] = (
        bruto[c_hora].fillna("").astype(str).str.strip() if c_hora else ""
    )
    df["Destino"] = (
        bruto[c_destino].fillna("SIN DESTINO").astype(str).str.upper().str.strip()
    )
    df["Proveedor"] = (
        bruto[c_proveedor].fillna("SIN PROVEEDOR").astype(str).str.upper().str.strip()
    )
    df["Bultos despachados"] = convertir_numero(bruto[c_bdesp])
    df["Valor despachado"] = convertir_numero(bruto[c_vdesp])
    df["Bultos empacados"] = convertir_numero(bruto[c_bemp])
    df["Valor empacado"] = convertir_numero(bruto[c_vemp])
    df["Bitácora"] = limpiar_identificador(bruto[c_bitacora])
    df["Bitacora clave"] = df["Bitácora"]
    df["Nro carga"] = limpiar_identificador(bruto[c_carga])

    costos = cargar_costos_flete(repo)
    df = aplicar_costos_flete(df, costos)

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
        {True: "Flete cruzado", False: "Sin costo encontrado"}
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
        "Base: /data/Costo_por_Servir_T1.csv · "
        "Flete: /data/COSTO FLETE T1.csv · "
        "Prioridad Nro de Carga, respaldo Bitacora"
    )

    if st.sidebar.button("🔄 Actualizar datos", key="actualizar_costo_servir"):
        st.rerun()

    df = cargar_costo_por_servir()

    if df.empty:
        st.warning("No existen registros validos para Costo por Servir T1.")
        return

    with st.sidebar:
        st.header("🔎 Filtros Costo por Servir")
        modo = st.radio(
            "Periodo", ["Día", "Semana", "Mes"], index=0, key="cps_periodo"
        )
        f = df.copy()

        if modo == "Día":
            fechas = sorted(f["Fecha"].dropna().unique())
            if fechas:
                fecha_sel = st.selectbox(
                    "Fecha", fechas, index=len(fechas) - 1, key="cps_fecha"
                )
                f = f[f["Fecha"] == fecha_sel]
        elif modo == "Semana":
            semanas = sorted(f["Año-Semana"].dropna().unique())
            if semanas:
                semana_sel = st.selectbox(
                    "Semana", semanas, index=len(semanas) - 1, key="cps_semana"
                )
                f = f[f["Año-Semana"] == semana_sel]
        else:
            meses = sorted(f["Mes"].dropna().unique())
            if meses:
                mes_sel = st.selectbox(
                    "Mes", meses, index=len(meses) - 1, key="cps_mes"
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
            ["Todos", "Flete cruzado", "Sin costo encontrado"],
            key="cps_estado",
        )

        busqueda = st.text_input(
            "Buscar carga o bitácora", key="cps_busqueda"
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

    # KPIs ponderados
    total_viajes = len(f)
    total_valor = f["Valor empacado"].sum()
    total_flete = f["Valor Flete"].sum()
    total_bultos = f["Bultos empacados"].sum()
    total_con_flete = int((f["Valor Flete"] > 0).sum())
    cxq_global = total_flete / total_valor if total_valor > 0 else 0
    cobertura = total_con_flete / total_viajes if total_viajes else 0

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("🚚 Viajes", formato_entero(total_viajes))
    c2.metric("📦 Bultos empacados", formato_entero(total_bultos))
    c3.metric("💵 Valor empacado", formato_clp(total_valor))
    c4.metric("🧾 Flete", formato_clp(total_flete))
    c5.metric(
        "📊 CxQ global",
        f"{cxq_global:.2%}" if total_valor > 0 else "Pendiente",
    )
    c6.metric("🔗 Cobertura flete", f"{cobertura:.1%}")

    st.divider()

    # Resumen por destino, con separador de miles.
    df_dest = resumen_destino(f)
    st.subheader("📋 Resumen por destino")
    if not df_dest.empty:
        tabla_dest = df_dest.copy()
        tabla_dest["Viajes"] = tabla_dest["Viajes"].map(formato_entero)
        tabla_dest["Bultos"] = tabla_dest["Bultos"].map(formato_entero)
        tabla_dest["Flete"] = tabla_dest["Flete"].map(formato_clp)
        tabla_dest["Valor empacado"] = tabla_dest["Valor_empacado"].map(formato_clp)
        tabla_dest["CxQ %"] = tabla_dest["CxQ"].map(lambda x: f"{x:.2%}")
        tabla_dest["Cobertura flete %"] = tabla_dest["Cobertura flete %"].map(
            lambda x: f"{x:.1f}%"
        )

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

    # Alertas
    st.subheader("🚨 Alertas automáticas")
    sin_flete = f[f["Valor Flete"] <= 0]
    sin_valor = f[f["Valor empacado"] <= 0]
    diferencia = f[f["Diferencia bultos"] != 0]

    if sin_flete.empty and sin_valor.empty and diferencia.empty:
        st.success("✅ Todos los viajes visibles están conciliados.")
    else:
        if not sin_flete.empty:
            st.error(
                f"🔴 {formato_entero(len(sin_flete))} viaje(s) sin costo de flete."
            )
        if not sin_valor.empty:
            st.warning(
                f"🟠 {formato_entero(len(sin_valor))} viaje(s) sin valor empacado."
            )
        if not diferencia.empty:
            st.warning(
                f"🟠 {formato_entero(len(diferencia))} viaje(s) con diferencia "
                "entre bultos despachados y empacados."
            )

    # Ranking
    st.subheader("🏆 Ranking automático")
    col_r1, col_r2 = st.columns(2)
    with col_r1:
        st.markdown("### 🔺 Top 5 mayor CxQ")
        top_cxq = df_dest[df_dest["Valor_empacado"] > 0].head(5).copy()
        top_cxq["CxQ"] = top_cxq["CxQ"].map(lambda x: f"{x:.2%}")
        top_cxq["Viajes"] = top_cxq["Viajes"].map(formato_entero)
        st.data_editor(
            top_cxq[["Destino", "Viajes", "CxQ"]],
            use_container_width=True,
            disabled=True,
            height=220,
            key="cps_ranking_cxq",
        )

    with col_r2:
        st.markdown("### 💵 Top 5 mayor flete")
        top_flete = df_dest.sort_values("Flete", ascending=False).head(5).copy()
        top_flete["Flete"] = top_flete["Flete"].map(formato_clp)
        top_flete["Viajes"] = top_flete["Viajes"].map(formato_entero)
        st.data_editor(
            top_flete[["Destino", "Viajes", "Flete"]],
            use_container_width=True,
            disabled=True,
            height=220,
            key="cps_ranking_flete",
        )

    # Graficos mantienen datos numericos.
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        st.subheader("📊 CxQ por destino")
        graf_dest = df_dest[df_dest["Valor_empacado"] > 0].copy()
        if not graf_dest.empty:
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
        if not df_prov.empty:
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
            fig_prov.update_xaxes(tickformat=",.0f", separatethousands=True)
            st.plotly_chart(fig_prov, use_container_width=True)

    # Detalle con miles separados por puntos.
    st.subheader("📄 Detalle de viajes")
    detalle = f.copy()
    detalle["Valor Flete"] = detalle["Valor Flete"].map(formato_clp)
    detalle["Valor despachado"] = detalle["Valor despachado"].map(formato_clp)
    detalle["Valor empacado"] = detalle["Valor empacado"].map(formato_clp)
    detalle["Bultos despachados"] = detalle["Bultos despachados"].map(formato_entero)
    detalle["Bultos empacados"] = detalle["Bultos empacados"].map(formato_entero)
    detalle["CxQ"] = detalle["CxQ"].map(
        lambda x: f"{x:.2%}" if x > 0 else "Pendiente"
    )

    columnas_detalle = [
        "Fecha de despacho", "Hora de despacho", "Destino", "Proveedor",
        "Valor Flete", "Bultos despachados", "Valor despachado",
        "Bultos empacados", "Valor empacado", "CxQ", "Bitácora",
        "Nro carga", "Origen Flete", "Estado cruce",
    ]

    st.data_editor(
        detalle[columnas_detalle],
        use_container_width=True,
        height=550,
        disabled=True,
        key="cps_detalle_final",
        column_config={
            "Nro carga": st.column_config.TextColumn("Nro carga", width="large"),
            "Proveedor": st.column_config.TextColumn("Proveedor", width="large"),
            "Origen Flete": st.column_config.TextColumn("Cruce utilizado"),
        },
    )

    # Descarga conserva valores numericos, no los textos formateados.
    st.download_button(
        "⬇️ Descargar CSV filtrado",
        data=f.drop(columns=["Bitacora clave"], errors="ignore")
        .to_csv(index=False)
        .encode("utf-8-sig"),
        file_name="Costo_por_Servir_T1_filtrado.csv",
        mime="text/csv",
        key="cps_descarga",
    )


if __name__ == "__main__":
    main()
