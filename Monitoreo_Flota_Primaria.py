import streamlit as st
import pandas as pd
from github import Github
from io import StringIO
from datetime import datetime
import pytz
from streamlit_autorefresh import st_autorefresh
import base64
import html

# =========================================================
# CONFIG
# =========================================================
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
REPO_NAME = "ErhickDiaz/COPIA-DASHBOARD_STREAMLIT_LOGISTIC"
GITHUB_FOLDER = "data"
ARCHIVO_MAXCUBE = "MAXCUBE_Primaria.csv"
ARCHIVO_TIEMPOS = "tiempos_viaje_destino.csv"
ZONA_HORARIA = "America/Santiago"

# Si un destino todavía no tiene horas definidas en la tabla, se usa este
# valor por defecto y la fila queda marcada con "⚠ SIN DATO".
DEFAULT_HORAS_VIAJE = 8.0

# Margen de tolerancia antes de marcar un despacho como "POSIBLE RETRASO"
# una vez pasada la hora estimada de llegada.
MARGEN_RETRASO_HORAS = 1.0

# Umbral para pasar de "EN RUTA" a "POR LLEGAR" (última hora antes del ETA).
UMBRAL_POR_LLEGAR_HORAS = 1.0


# =========================================================
# HELPERS COMPARTIDOS (mismo patrón que el resto de módulos)
# =========================================================
def load_css_inline():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@600;700&family=Share+Tech+Mono&display=swap');

        :root{
            --board-bg:#0A0F1E;
            --board-panel:#0F1730;
            --board-row-alt:#121C3B;
            --board-divider:rgba(255,255,255,0.08);
            --board-amber:#FFB300;
            --board-cyan:#7DD8E8;
            --board-green:#4ADE80;
            --board-red:#FF4D5E;
            --board-dim:#5B6683;
        }

        .board-wrap{
            background:var(--board-bg);
            border:1px solid var(--board-divider);
            border-radius:10px;
            padding:0 0 6px 0;
            overflow:hidden;
            box-shadow:0 20px 50px rgba(0,0,0,0.35);
        }

        .board-topbar{
            display:flex;
            justify-content:space-between;
            align-items:baseline;
            padding:18px 26px 10px 26px;
            border-bottom:1px solid var(--board-divider);
        }

        .board-title{
            font-family:'Barlow Condensed',sans-serif;
            font-weight:700;
            text-transform:uppercase;
            letter-spacing:3px;
            font-size:22px;
            color:#EAF2FF;
        }

        .board-clock{
            font-family:'Share Tech Mono',monospace;
            font-size:22px;
            color:var(--board-amber);
            letter-spacing:2px;
        }

        .board-header-row, .board-row{
            display:grid;
            grid-template-columns: 30% 16% 16% 20% 18%;
            align-items:center;
            padding:10px 26px;
        }

        .board-header-row{
            font-family:'Barlow Condensed',sans-serif;
            font-weight:600;
            text-transform:uppercase;
            letter-spacing:2px;
            font-size:13px;
            color:var(--board-cyan);
            border-bottom:1px solid var(--board-divider);
        }

        .board-row{
            font-family:'Share Tech Mono',monospace;
            font-size:16px;
            color:var(--board-amber);
            border-bottom:1px solid var(--board-divider);
            position:relative;
        }

        .board-row:nth-child(even){ background:var(--board-row-alt); }

        .board-row.next-up{ border-left:3px solid var(--board-amber); }
        .board-row.next-up::before{
            content:"";
            position:absolute;
            left:-1px; top:0; bottom:0;
            width:3px;
            background:var(--board-amber);
            animation:board-pulse 2.4s ease-in-out infinite;
        }

        @keyframes board-pulse{
            0%,100%{ opacity:1; }
            50%{ opacity:.35; }
        }

        @media (prefers-reduced-motion: reduce){
            .board-row.next-up::before{ animation:none; }
        }

        .board-destino{ display:flex; flex-direction:column; }
        .board-destino .carga{
            font-size:11px;
            color:var(--board-dim);
            letter-spacing:1px;
        }
        .board-destino .sindato{
            font-size:10px;
            color:var(--board-red);
            letter-spacing:1px;
        }

        .board-chip{
            display:inline-block;
            padding:3px 10px;
            border-radius:3px;
            font-size:12px;
            letter-spacing:1px;
            border:1px solid currentColor;
        }
        .chip-enruta{ color:var(--board-cyan); }
        .chip-porllegar{ color:var(--board-amber); }
        .chip-llegado{ color:var(--board-green); }
        .chip-retraso{ color:var(--board-red); }

        .board-empty{
            font-family:'Share Tech Mono',monospace;
            color:var(--board-dim);
            padding:30px 26px;
            text-align:center;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def load_image(image_file):
    with open(image_file, "rb") as f:
        data = f.read()
        return base64.b64encode(data).decode()


def normalizar_destino(destino):
    destino = str(destino).upper().replace("\xa0", " ").strip()
    destino = " ".join(destino.split())
    partes = [p.strip() for p in destino.split("/") if p.strip()]
    return " / ".join(partes)


def leer_csv_github(repo, filename):
    try:
        file_content = repo.get_contents(f"{GITHUB_FOLDER}/{filename}")
        csv_string = file_content.decoded_content.decode("utf-8")
        return pd.read_csv(StringIO(csv_string))
    except Exception as e:
        st.error(f"No se pudo cargar {filename} desde GitHub: {e}")
        return pd.DataFrame()


# =========================================================
# CARGA Y CÁLCULO DE ETA
# =========================================================
@st.cache_data(ttl=55)
def cargar_datos_eta():
    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(REPO_NAME)

    df = leer_csv_github(repo, ARCHIVO_MAXCUBE)
    tiempos = leer_csv_github(repo, ARCHIVO_TIEMPOS)

    if df.empty:
        return df

    df.columns = [c.strip() for c in df.columns]

    # ── Fecha + hora de despacho combinadas ──
    df["Fecha de despacho"] = pd.to_datetime(df["Fecha de despacho"], dayfirst=True, errors="coerce")
    df["Hora de despacho"] = df["Hora de despacho"].astype(str).str.strip()
    df["Fecha_Hora_Despacho"] = pd.to_datetime(
        df["Fecha de despacho"].dt.strftime("%d/%m/%Y") + " " + df["Hora de despacho"],
        dayfirst=True, errors="coerce"
    )

    # ── Destino normalizado (misma lógica que MaxCube_Primaria) ──
    df["Destino Agencia concat"] = (
        df["Destino Agencia concat"].astype(str)
        .str.upper().str.replace("\xa0", " ", regex=False).str.strip()
    )
    df["Destino Norm"] = df["Destino Agencia concat"].apply(normalizar_destino)

    # ── Tabla de horas por destino ──
    if not tiempos.empty:
        tiempos.columns = [c.strip() for c in tiempos.columns]
        tiempos["Destino Norm"] = tiempos["Destino"].apply(normalizar_destino)
        tiempos["Horas_Estimadas"] = pd.to_numeric(tiempos["Horas_Estimadas"], errors="coerce")
        mapa_horas = dict(zip(tiempos["Destino Norm"], tiempos["Horas_Estimadas"]))
    else:
        mapa_horas = {}

    df["Horas Viaje"] = df["Destino Norm"].map(mapa_horas)
    df["Sin Dato"] = df["Horas Viaje"].isna()
    df["Horas Viaje"] = df["Horas Viaje"].fillna(DEFAULT_HORAS_VIAJE)

    df["ETA"] = df["Fecha_Hora_Despacho"] + pd.to_timedelta(df["Horas Viaje"], unit="h")

    return df.dropna(subset=["Fecha_Hora_Despacho", "ETA"])


def formatear_delta(delta_seg):
    signo = "-" if delta_seg < 0 else ""
    delta_seg = abs(int(delta_seg))
    horas, resto = divmod(delta_seg, 3600)
    minutos = resto // 60
    return f"{signo}{horas}h {minutos:02d}m"


def calcular_estado(eta, now):
    delta = (eta - now).total_seconds()
    if delta > UMBRAL_POR_LLEGAR_HORAS * 3600:
        return "EN RUTA", "chip-enruta", f"Llega en {formatear_delta(delta)}"
    elif delta > 0:
        return "POR LLEGAR", "chip-porllegar", f"Llega en {formatear_delta(delta)}"
    elif delta > -MARGEN_RETRASO_HORAS * 3600:
        return "ARRIBO ESTIMADO", "chip-llegado", f"Hace {formatear_delta(-delta)}"
    else:
        return "POSIBLE RETRASO", "chip-retraso", f"Atrasado {formatear_delta(-delta)}"


# =========================================================
# APP
# =========================================================
def main():
    def load_css(file_name):
        with open(file_name) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

    load_css("style.css")
    load_css_inline()

    chile_tz = pytz.timezone(ZONA_HORARIA)
    now = datetime.now(chile_tz)
    st.session_state["ultima_actualizacion_real"] = now

    st.sidebar.image("OsitoTierno.png", use_column_width=True)

    logo_base64 = load_image("IDEAL.jfif")
    st.markdown(f"""
        <div style="display: flex; align-items: center;">
            <img src="data:image/jpeg;base64,{logo_base64}" style="width: 220px; margin-right: 15px;">
            <h1>Logística: ETA Flota Primaria</h1>
        </div>
    """, unsafe_allow_html=True)

    st.caption("Fuente: GitHub /data/MAXCUBE_Primaria.csv + /data/tiempos_viaje_destino.csv")

    st_autorefresh(interval=60000, key="eta_refresh")

    df = cargar_datos_eta()

    if df.empty:
        st.warning("⚠️ No hay datos disponibles todavía.")
        return

    # ── FILTROS ──
    with st.sidebar:
        st.header("🔎 Filtros")
        fechas_validas = sorted(df["Fecha_Hora_Despacho"].dt.date.dropna().unique())
        fecha_sel = st.selectbox(
            "Fecha de despacho", fechas_validas,
            index=len(fechas_validas) - 1 if fechas_validas else 0
        )
        f = df[df["Fecha_Hora_Despacho"].dt.date == fecha_sel].copy()

        destinos = sorted(f["Destino Norm"].dropna().unique())
        destino_sel = st.multiselect("Destino", destinos)
        if destino_sel:
            f = f[f["Destino Norm"].isin(destino_sel)]

    # ── ESTADO POR FILA ──
    estados = f["ETA"].apply(lambda eta: calcular_estado(eta, now))
    f["Estado"] = [e[0] for e in estados]
    f["Estado Clase"] = [e[1] for e in estados]
    f["Tiempo"] = [e[2] for e in estados]

    estado_sel = st.sidebar.multiselect("Estado", sorted(f["Estado"].unique()))
    if estado_sel:
        f = f[f["Estado"].isin(estado_sel)]

    f = f.sort_values("ETA", ascending=True)

    # ── KPIs ──
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🚛 Despachos", len(f))
    c2.metric("🛫 En ruta", int((f["Estado"] == "EN RUTA").sum()))
    c3.metric("🟡 Por llegar", int((f["Estado"] == "POR LLEGAR").sum()))
    c4.metric("🔴 Posible retraso", int((f["Estado"] == "POSIBLE RETRASO").sum()))

    sin_dato = sorted(f.loc[f["Sin Dato"], "Destino Norm"].unique())
    if sin_dato:
        st.info(
            "⚠️ Estos destinos aún no tienen horas definidas en `data/tiempos_viaje_destino.csv` "
            f"(se usó el valor por defecto de {DEFAULT_HORAS_VIAJE:.0f} h): "
            + ", ".join(sin_dato)
        )

    # ── TABLERO ──
    filas_html = ""
    if f.empty:
        filas_html = '<div class="board-empty">Sin despachos para los filtros seleccionados</div>'
    else:
        primera_id = f.index[0]
        for idx, row in f.iterrows():
            next_up = " next-up" if idx == primera_id and row["Estado"] in ("EN RUTA", "POR LLEGAR") else ""
            sin_dato_tag = '<div class="sindato">⚠ SIN DATO</div>' if row["Sin Dato"] else ""
            destino = html.escape(str(row["Destino Norm"]))
            carga = html.escape(str(row.get("Nro carga", "")))
            salida = row["Fecha_Hora_Despacho"].strftime("%d-%m %H:%M")
            eta_str = row["ETA"].strftime("%d-%m %H:%M")

            filas_html += f"""
            <div class="board-row{next_up}">
                <div class="board-destino">
                    <div>{destino}</div>
                    <div class="carga">{carga}</div>
                    {sin_dato_tag}
                </div>
                <div>{salida}</div>
                <div>{eta_str}</div>
                <div>{row['Tiempo']}</div>
                <div><span class="board-chip {row['Estado Clase']}">{row['Estado']}</span></div>
            </div>
            """

    st.markdown(
        f"""
        <div class="board-wrap">
            <div class="board-topbar">
                <div class="board-title">Próximos arribos · Transporte Primaria</div>
                <div class="board-clock">{now.strftime('%d-%m-%Y %H:%M:%S')}</div>
            </div>
            <div class="board-header-row">
                <div>Destino</div>
                <div>Salida</div>
                <div>ETA</div>
                <div>Tiempo</div>
                <div>Estado</div>
            </div>
            {filas_html}
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.download_button(
        "⬇️ Descargar CSV filtrado",
        data=f.to_csv(index=False).encode("utf-8"),
        file_name="eta_flota_primaria_filtrado.csv",
        mime="text/csv"
    )


if __name__ == "__main__":
    main()
