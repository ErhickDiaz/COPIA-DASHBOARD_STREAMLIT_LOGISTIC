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
ARCHIVO_COSTO_FLETE = "viajes_primaria.csv"
ARCHIVO_FLETE_ACTUAL = "fletes_actuales.csv"
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
        primera = contenido.splitlines()[0] if contenido.splitlines() else ""
        sep = ";" if primera.count(";") > primera.count(",") else ","
        return pd.read_csv(StringIO(contenido), sep=sep, engine="python", dtype=str)
    except Exception as e:
        st.error(f"No se pudo cargar {filename} desde GitHub: {e}")
        return pd.DataFrame()

# =========================================================
# NORMALIZACION
# =========================================================
def normalizar_texto(valor):
    texto = unicodedata.normalize("NFD", str(valor).strip().lower())
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", " ", texto).strip()


def buscar_columna(df, opciones, obligatoria=True):
    mapa = {normalizar_texto(c): c for c in df.columns}
    for op in opciones:
        if normalizar_texto(op) in mapa:
            return mapa[normalizar_texto(op)]
    for clave, original in mapa.items():
        if any(normalizar_texto(op) in clave for op in opciones):
            return original
    if obligatoria:
        raise KeyError(f"No se encontro columna equivalente a {opciones}. Disponibles: {list(df.columns)}")
    return None


def limpiar_identificador(serie):
    return (serie.fillna("").astype(str)
            .str.replace('="', "", regex=False).str.replace('"', "", regex=False)
            .str.replace(r"\.0$", "", regex=True).str.replace(" ", " ", regex=False)
            .str.strip().str.upper())


def normalizar_carga(serie):
    return (limpiar_identificador(serie)
            .str.replace(r"\s*/\s*", " / ", regex=True)
            .str.replace(r"\s+", " ", regex=True).str.strip())


def normalizar_clave_texto(serie):
    return (serie.fillna("").astype(str).str.replace(" ", " ", regex=False)
            .str.upper().str.strip().str.replace(r"\s+", " ", regex=True)
            .str.replace(r"\s*/\s*", "/", regex=True))


def normalizar_destino_clave(serie):
    """Normaliza destinos para cruzar MAXCUBE con fletes_actuales.csv.

    Convierte rutas expresadas con '/', guion o guion bajo a una clave comun.
    Ejemplos: CONCEPCION / TEMUCO y CONCEPCION - TEMUCO.
    """
    normalizado = normalizar_clave_texto(serie)
    return (
        normalizado
        .str.replace(r"\_", " ", regex=True)
        .str.replace("_", " ", regex=False)
        .str.replace(r"\s*/\s*", " - ", regex=True)
        .str.replace(r"\s+-\s+", " - ", regex=True)
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
    )


def convertir_numero(serie):
    if pd.api.types.is_numeric_dtype(serie):
        return pd.to_numeric(serie, errors="coerce").fillna(0.0)
    limpio = (serie.fillna("").astype(str).str.replace('="', "", regex=False)
              .str.replace('"', "", regex=False).str.replace("$", "", regex=False)
              .str.replace("CLP", "", regex=False).str.replace(" ", "", regex=False).str.strip())
    def uno(v):
        if not v or v.lower() in {"nan", "none", "null", "-", "#¡ref!"}:
            return 0.0
        try:
            if "," in v:
                return float(v.replace(".", "").replace(",", "."))
            if re.fullmatch(r"-?\d{1,3}(\.\d{3})+", v):
                return float(v.replace(".", ""))
            if v.count(".") > 1:
                return float(v.replace(".", ""))
            return float(v)
        except (ValueError, TypeError):
            return 0.0
    return limpio.apply(uno)


def formato_entero(v):
    return f"{float(v):,.0f}".replace(",", ".")


def formato_clp(v):
    return f"$ {formato_entero(v)}"


def calcular_semana_bimbo(fecha):
    if pd.isna(fecha):
        return None
    anio = fecha.year
    inicio = pd.Timestamp(f"{anio}-01-01")
    primer_jueves = inicio + pd.Timedelta(days=(3 - inicio.weekday()) % 7)
    if fecha < primer_jueves:
        anio -= 1
        inicio = pd.Timestamp(f"{anio}-01-01")
        primer_jueves = inicio + pd.Timedelta(days=(3 - inicio.weekday()) % 7)
    return f"{anio}-S{str(((fecha-primer_jueves).days // 7)+1).zfill(2)}"

# =========================================================
# FUENTE 1: VIAJES_PRIMARIA
# =========================================================
def cargar_costos_flete(repo):
    bruto = leer_csv_github(repo, ARCHIVO_COSTO_FLETE)
    if bruto.empty:
        return bruto
    bruto.columns = [str(c).strip() for c in bruto.columns]
    try:
        c_carga = buscar_columna(bruto, ["Nro Carga", "Nro de Carga", "Numero carga"], False)
        c_bit = buscar_columna(bruto, ["Bitacora", "Bitácora", "Nro Bitacora"], False)
        c_costo = buscar_columna(bruto, ["COSTOS", "COSTO", "Costo Flete", "Valor Flete", "Flete"])
    except KeyError as e:
        st.error(f"Error en {ARCHIVO_COSTO_FLETE}: {e}")
        return pd.DataFrame()
    if not c_carga and not c_bit:
        st.error(f"{ARCHIVO_COSTO_FLETE} no contiene Nro Carga ni Bitacora")
        return pd.DataFrame()
    out = pd.DataFrame(index=bruto.index)
    out["Nro carga"] = normalizar_carga(bruto[c_carga]) if c_carga else ""
    out["Bitacora"] = limpiar_identificador(bruto[c_bit]) if c_bit else ""
    out["COSTO"] = convertir_numero(bruto[c_costo])
    return out[out["COSTO"] > 0].copy()

# =========================================================
# FUENTE 2: FLETE ACTUAL
# Cruce exacto: PROVEEDOR + DESTINO -> COSTOS
# =========================================================
def cargar_flete_actual(repo):
    bruto = leer_csv_github(repo, ARCHIVO_FLETE_ACTUAL)
    if bruto.empty:
        return bruto
    bruto.columns = [str(c).strip() for c in bruto.columns]
    try:
        c_prov = buscar_columna(bruto, ["PROVEEDOR", "Proveedor", "Carrier", "Transportista"])
        c_dest = buscar_columna(bruto, ["DESTINO", "Destino", "1ra Parada", "Primera Parada"])
        c_costo = buscar_columna(bruto, ["COSTOS", "COSTO", "Costo Flete", "Valor Flete", "Flete"])
    except KeyError as e:
        st.error(f"Error en {ARCHIVO_FLETE_ACTUAL}: {e}")
        return pd.DataFrame()
    out = pd.DataFrame(index=bruto.index)
    out["Proveedor clave"] = normalizar_clave_texto(bruto[c_prov])
    out["Destino clave"] = normalizar_destino_clave(bruto[c_dest])
    out["COSTO"] = convertir_numero(bruto[c_costo])
    out = out[(out["Proveedor clave"] != "") & (out["Destino clave"] != "") & (out["COSTO"] > 0)]
    return out.drop_duplicates(["Proveedor clave", "Destino clave"], keep="last")


def crear_mapa_unico(df, clave):
    if df.empty or clave not in df.columns:
        return {}
    x = df[df[clave].astype(str).str.strip().ne("")]
    return x.drop_duplicates(clave, keep="last").set_index(clave)["COSTO"].to_dict()


def crear_mapa_actual(df):
    if df.empty:
        return {}
    return df.set_index(["Proveedor clave", "Destino clave"])["COSTO"].to_dict()


def aplicar_costos_flete(df, viajes, actual):
    out = df.copy()
    mapa_carga = crear_mapa_unico(viajes, "Nro carga")
    mapa_bit = crear_mapa_unico(viajes, "Bitacora")
    mapa_actual = crear_mapa_actual(actual)

    por_carga = out["Nro carga"].map(mapa_carga)
    por_bit = out["Bitacora clave"].map(mapa_bit)
    claves = pd.Series(list(zip(out["Proveedor clave"], out["Destino clave"])), index=out.index)
    por_actual = claves.map(mapa_actual)

    out["Valor Flete"] = por_carga
    out["Origen Flete"] = "Sin coincidencia"
    m1 = por_carga.notna() & por_carga.gt(0)
    out.loc[m1, "Origen Flete"] = "viajes_primaria - Nro Carga"

    m2 = (out["Valor Flete"].isna() | out["Valor Flete"].le(0)) & por_bit.notna() & por_bit.gt(0)
    out.loc[m2, "Valor Flete"] = por_bit.loc[m2]
    out.loc[m2, "Origen Flete"] = "viajes_primaria - Bitacora"

    m3 = (out["Valor Flete"].isna() | out["Valor Flete"].le(0)) & por_actual.notna() & por_actual.gt(0)
    out.loc[m3, "Valor Flete"] = por_actual.loc[m3]
    out.loc[m3, "Origen Flete"] = "flete_actual - Proveedor/Destino"

    out["Valor Flete"] = pd.to_numeric(out["Valor Flete"], errors="coerce").fillna(0.0)
    return out

# =========================================================
# CONSOLIDADO
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
        c_dest = buscar_columna(bruto, ["Destino", "Destino Agencia concat"])
        c_prov = buscar_columna(bruto, ["Proveedor", "PROVEEDOR"])
        c_bd = buscar_columna(bruto, ["Bultos despachados"])
        c_vd = buscar_columna(bruto, ["Costo de los bultos despachados", "Valor despachado"])
        c_be = buscar_columna(bruto, ["Bultos empacados"])
        c_ve = buscar_columna(bruto, ["Costo de los bultos empacados", "Valor empacado"])
        c_bit = buscar_columna(bruto, ["Bitacora", "Bitácora"])
        c_carga = buscar_columna(bruto, ["Nro carga", "Nro de Carga", "Numero carga"])
    except KeyError as e:
        st.error(str(e)); return pd.DataFrame()

    df = pd.DataFrame(index=bruto.index)
    df["Fecha despacho dt"] = pd.to_datetime(bruto[c_fecha], dayfirst=True, errors="coerce")
    df["Fecha de despacho"] = df["Fecha despacho dt"].dt.strftime("%d/%m/%Y")
    df["Hora de despacho"] = bruto[c_hora].fillna("").astype(str).str.strip() if c_hora else ""
    df["Destino"] = bruto[c_dest].fillna("SIN DESTINO").astype(str).str.upper().str.strip()
    df["Proveedor"] = bruto[c_prov].fillna("SIN PROVEEDOR").astype(str).str.upper().str.strip()
    df["Destino clave"] = normalizar_destino_clave(bruto[c_dest])
    df["Proveedor clave"] = normalizar_clave_texto(bruto[c_prov])
    df["Bultos despachados"] = convertir_numero(bruto[c_bd])
    df["Valor despachado"] = convertir_numero(bruto[c_vd])
    df["Bultos empacados"] = convertir_numero(bruto[c_be])
    df["Valor empacado"] = convertir_numero(bruto[c_ve])
    df["Bitácora"] = limpiar_identificador(bruto[c_bit])
    df["Bitacora clave"] = df["Bitácora"]
    df["Nro carga"] = normalizar_carga(bruto[c_carga])

    viajes = cargar_costos_flete(repo)
    actual = cargar_flete_actual(repo)
    df = aplicar_costos_flete(df, viajes, actual)

    df["Fecha"] = df["Fecha despacho dt"].dt.date
    df["Año-Semana"] = df["Fecha despacho dt"].apply(calcular_semana_bimbo)
    df["Mes"] = df["Fecha despacho dt"].dt.strftime("%Y-%m")
    df["Diferencia bultos"] = df["Bultos despachados"] - df["Bultos empacados"]
    df["CxQ"] = 0.0
    m = df["Valor empacado"] > 0
    df.loc[m, "CxQ"] = df.loc[m, "Valor Flete"] / df.loc[m, "Valor empacado"]
    df["Estado cruce"] = df["Valor Flete"].gt(0).map({True:"Flete cruzado", False:"Sin costo encontrado"})
    return df.sort_values(["Fecha despacho dt", "Destino", "Bitácora", "Nro carga"])

# =========================================================
# RESUMENES
# =========================================================
def resumen_destino(df):
    if df.empty: return pd.DataFrame()
    r = df.groupby("Destino", as_index=False).agg(Viajes=("Nro carga","count"), Flete=("Valor Flete","sum"), Valor_empacado=("Valor empacado","sum"), Bultos=("Bultos empacados","sum"), Con_flete=("Valor Flete",lambda s:int((s>0).sum())))
    r["CxQ"] = 0.0
    m = r["Valor_empacado"] > 0
    r.loc[m,"CxQ"] = r.loc[m,"Flete"] / r.loc[m,"Valor_empacado"]
    r["Cobertura flete %"] = (r["Con_flete"] / r["Viajes"] * 100).round(1)
    return r.sort_values("CxQ", ascending=False)


def resumen_proveedor(df):
    if df.empty: return pd.DataFrame()
    r = df.groupby("Proveedor", as_index=False).agg(Viajes=("Nro carga","count"), Flete=("Valor Flete","sum"), Valor_empacado=("Valor empacado","sum"))
    r["CxQ"] = 0.0
    m = r["Valor_empacado"] > 0
    r.loc[m,"CxQ"] = r.loc[m,"Flete"] / r.loc[m,"Valor_empacado"]
    return r.sort_values("Flete", ascending=False)

# =========================================================
# APP
# =========================================================
def main():
    st.session_state["ultima_actualizacion_real"] = datetime.now(pytz.timezone(ZONA_HORARIA))
    st.title("💰 Costo por Servir T1")
    st.warning(f"Archivo histórico: {ARCHIVO_COSTO_FLETE}")

    st.caption(f"Base: /data/{ARCHIVO_COSTO_SERVIR} · Flete histórico: /data/{ARCHIVO_COSTO_FLETE} · Respaldo: /data/{ARCHIVO_FLETE_ACTUAL} · Prioridad: Nro Carga, Bitácora y tarifa actual")
    if st.sidebar.button("🔄 Actualizar datos", key="actualizar_costo_servir"):
        st.rerun()
    df = cargar_costo_por_servir()
    if df.empty:
        st.warning("No existen registros validos para Costo por Servir T1."); return

    with st.sidebar:
        st.header("🔎 Filtros Costo por Servir")
        modo = st.radio("Periodo", ["Día","Semana","Mes"], key="cps_periodo")
        f = df.copy()
        if modo == "Día":
            vals = sorted(f["Fecha"].dropna().unique())
            if vals: f = f[f["Fecha"] == st.selectbox("Fecha", vals, index=len(vals)-1, key="cps_fecha")]
        elif modo == "Semana":
            vals = sorted(f["Año-Semana"].dropna().unique())
            if vals: f = f[f["Año-Semana"] == st.selectbox("Semana", vals, index=len(vals)-1, key="cps_semana")]
        else:
            vals = sorted(f["Mes"].dropna().unique())
            if vals: f = f[f["Mes"] == st.selectbox("Mes", vals, index=len(vals)-1, key="cps_mes")]
        ds = st.multiselect("Destino", sorted(f["Destino"].unique()), key="cps_destino")
        ps = st.multiselect("Proveedor", sorted(f["Proveedor"].unique()), key="cps_proveedor")
        es = st.selectbox("Cruce de flete", ["Todos","Flete cruzado","Sin costo encontrado"], key="cps_estado")
        q = st.text_input("Buscar carga o bitácora", key="cps_busqueda").strip().lower()
        if ds: f = f[f["Destino"].isin(ds)]
        if ps: f = f[f["Proveedor"].isin(ps)]
        if es != "Todos": f = f[f["Estado cruce"] == es]
        if q: f = f[f["Nro carga"].str.lower().str.contains(q,na=False,regex=False) | f["Bitácora"].str.lower().str.contains(q,na=False,regex=False)]

    total_viajes=len(f); total_valor=f["Valor empacado"].sum(); total_flete=f["Valor Flete"].sum(); total_bultos=f["Bultos empacados"].sum()
    cxq=total_flete/total_valor if total_valor>0 else 0; cobertura=(f["Valor Flete"]>0).mean() if total_viajes else 0
    c1,c2,c3,c4,c5,c6=st.columns(6)
    c1.metric("🚚 Viajes",formato_entero(total_viajes)); c2.metric("📦 Bultos",formato_entero(total_bultos)); c3.metric("💵 Valor empacado",formato_clp(total_valor)); c4.metric("🧾 Flete",formato_clp(total_flete)); c5.metric("📊 CxQ global",f"{cxq:.2%}" if total_valor>0 else "Pendiente"); c6.metric("🔗 Cobertura",f"{cobertura:.1%}")

    st.subheader("📋 Conciliación de fuentes de flete")
    rf=f.groupby("Origen Flete",as_index=False).agg(Viajes=("Nro carga","count"),Flete=("Valor Flete","sum"))
    rf["Viajes"]=rf["Viajes"].map(formato_entero); rf["Flete"]=rf["Flete"].map(formato_clp)
    st.data_editor(rf,use_container_width=True,disabled=True,hide_index=True,key="cps_fuentes_flete")

    rd=resumen_destino(f)
    st.subheader("📋 Resumen por destino")
    vista=rd.copy(); vista["Viajes"]=vista["Viajes"].map(formato_entero); vista["Bultos"]=vista["Bultos"].map(formato_entero); vista["Flete"]=vista["Flete"].map(formato_clp); vista["Valor empacado"]=vista["Valor_empacado"].map(formato_clp); vista["CxQ %"]=vista["CxQ"].map(lambda x:f"{x:.2%}"); vista["Cobertura flete %"]=vista["Cobertura flete %"].map(lambda x:f"{x:.1f}%")
    st.data_editor(vista[["Destino","Viajes","Bultos","Flete","Valor empacado","CxQ %","Cobertura flete %"]],use_container_width=True,disabled=True,height=420,key="cps_resumen_destino")

    st.subheader("🚨 Alertas automáticas")
    sf=f[f["Valor Flete"]<=0]; sv=f[f["Valor empacado"]<=0]; db=f[f["Diferencia bultos"]!=0]
    if sf.empty and sv.empty and db.empty: st.success("✅ Todos los viajes visibles están conciliados.")
    else:
        if not sf.empty: st.error(f"🔴 {formato_entero(len(sf))} viaje(s) sin costo de flete.")
        if not sv.empty: st.warning(f"🟠 {formato_entero(len(sv))} viaje(s) sin valor empacado.")
        if not db.empty: st.warning(f"🟠 {formato_entero(len(db))} viaje(s) con diferencia de bultos.")

    col1,col2=st.columns(2)
    with col1:
        st.subheader("📊 CxQ por destino")
        gd=rd[rd["Valor_empacado"]>0]
        if not gd.empty:
            fig=px.bar(gd.sort_values("CxQ"),x="CxQ",y="Destino",orientation="h",text_auto=".2%",color="CxQ",color_continuous_scale="RdYlGn_r")
            fig.update_xaxes(tickformat=".1%"); fig.update_layout(height=560,coloraxis_showscale=False); st.plotly_chart(fig,use_container_width=True)
    with col2:
        st.subheader("💵 Flete por proveedor")
        rp=resumen_proveedor(f)
        if not rp.empty:
            fig=px.bar(rp.sort_values("Flete"),x="Flete",y="Proveedor",orientation="h",color="CxQ",color_continuous_scale="Tealgrn")
            fig.update_xaxes(tickformat=",.0f",separatethousands=True); fig.update_layout(height=560); st.plotly_chart(fig,use_container_width=True)

    st.subheader("📄 Detalle de viajes")
    det=f.copy(); det["Valor Flete"]=det["Valor Flete"].map(formato_clp); det["Valor despachado"]=det["Valor despachado"].map(formato_clp); det["Valor empacado"]=det["Valor empacado"].map(formato_clp); det["Bultos despachados"]=det["Bultos despachados"].map(formato_entero); det["Bultos empacados"]=det["Bultos empacados"].map(formato_entero); det["CxQ"]=det["CxQ"].map(lambda x:f"{x:.2%}" if x>0 else "Pendiente")
    cols=["Fecha de despacho","Hora de despacho","Destino","Proveedor","Valor Flete","Bultos despachados","Valor despachado","Bultos empacados","Valor empacado","CxQ","Bitácora","Nro carga","Origen Flete","Estado cruce"]
    st.data_editor(det[cols],use_container_width=True,height=550,disabled=True,key="cps_detalle_final")
    st.download_button("⬇️ Descargar CSV filtrado",data=f.drop(columns=["Bitacora clave","Proveedor clave","Destino clave"],errors="ignore").to_csv(index=False).encode("utf-8-sig"),file_name="Costo_por_Servir_T1_filtrado.csv",mime="text/csv",key="cps_descarga")

if __name__ == "__main__":
    main()
